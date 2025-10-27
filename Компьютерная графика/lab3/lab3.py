# Lab 3: Shadow Mapping (Torus in front, Teapot behind it + Floor)
# Управление: ЛКМ/колесо/R; W/A/S/D/Q/E; +/-; 1-5; O; P; [; ]

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import numpy as np
import sys

# -------------------- Window --------------------
window_width = 1400
window_height = 900

# -------------------- Camera --------------------
mouse_down = False
mouse_x = 0
mouse_y = 0
rotation_x = 30.0
rotation_y = 45.0
zoom = 1.0

def apply_camera_rotation():
    distance = 14.0 * zoom
    rx = np.radians(rotation_x)
    ry = np.radians(rotation_y)
    cam_x = distance * np.sin(ry) * np.cos(rx)
    cam_y = distance * np.sin(rx)
    cam_z = distance * np.cos(ry) * np.cos(rx)
    return cam_x, cam_y, cam_z

# -------------------- Light --------------------
light_x = 5.0
light_y = 8.0
light_z = 5.0
light_intensity = 1.0
light_color = [1.0, 1.0, 1.0]

# -------------------- Shadow map --------------------
SHADOW_MAP_SIZE = 2048
depth_fbo = None
depth_tex = None
shadow_enabled = True
pcf_enabled = True
shadow_bias = 0.004

# -------------------- Programs --------------------
prog_depth = None
prog_scene = None

# -------------------- Materials --------------------
mat_ico   = {"ambient": (0.10, 0.40, 0.70), "diffuse": (0.20, 0.60, 1.00), "specular": (0.50, 0.50, 0.80), "shininess": 30.0,  "alpha": 0.30}
mat_teapot= {"ambient": (0.25, 0.00, 0.25), "diffuse": (1.00, 0.00, 1.00), "specular": (1.00, 1.00, 1.00), "shininess": 128.0, "alpha": 1.00}
mat_torus = {"ambient": (0.30, 0.30, 0.30), "diffuse": (0.80, 0.80, 0.80), "specular": (0.10, 0.10, 0.10), "shininess": 5.0,   "alpha": 1.00}
mat_plane = {"ambient": (0.25, 0.25, 0.25), "diffuse": (0.70, 0.70, 0.70), "specular": (0.05, 0.05, 0.05), "shininess": 4.0,   "alpha": 1.00}

# -------------------- Shaders --------------------
vs_depth = """
#version 120
void main() { gl_Position = ftransform(); }
"""
fs_depth = """
#version 120
void main() { }
"""

vs_scene = """
#version 120
uniform mat4 uLightVP;
uniform mat4 uModel;

varying vec3 vNormalEye;
varying vec3 vPosEye;
varying vec4 vPosLight;

void main() {
    vec4 posEye = gl_ModelViewMatrix * gl_Vertex;
    vPosEye = posEye.xyz;
    vNormalEye = normalize(gl_NormalMatrix * gl_Normal);
    vPosLight = uLightVP * uModel * gl_Vertex;
    gl_Position = ftransform();
}
"""

fs_scene = """
#version 120
uniform sampler2D uShadowMap;

uniform vec3  uLightPosEye;
uniform vec3  uViewPosEye;
uniform vec3  uLightColor;
uniform float uLightIntensity;

uniform float uBias;
uniform int   uUseShadows;
uniform int   uUsePCF;

uniform vec3  uKa, uKd, uKs;
uniform float uShininess;
uniform float uAlpha;

varying vec3 vNormalEye;
varying vec3 vPosEye;
varying vec4 vPosLight;

float tapShadow(vec2 uv, float compareDepth, float bias) {
    float d = texture2D(uShadowMap, uv).r;
    return (compareDepth - bias) > d ? 1.0 : 0.0;
}

float computeShadow(vec4 lsPos) {
    vec3 proj = lsPos.xyz / lsPos.w;
    proj = proj * 0.5 + 0.5;
    if (proj.x < 0.0 || proj.x > 1.0 || proj.y < 0.0 || proj.y > 1.0 || proj.z > 1.0) return 0.0;
    if (uUsePCF == 1) {
        float texel = 1.0 / float(%d);
        float s = 0.0;
        for (int x = -1; x <= 1; ++x)
            for (int y = -1; y <= 1; ++y)
                s += tapShadow(proj.xy + vec2(float(x), float(y))*texel, proj.z, uBias);
        return s / 9.0;
    } else {
        return tapShadow(proj.xy, proj.z, uBias);
    }
}

void main() {
    vec3 N = normalize(vNormalEye);
    vec3 P = vPosEye;
    vec3 V = normalize(uViewPosEye - P);
    vec3 L = normalize(uLightPosEye - P);

    float NdotL = max(dot(N, L), 0.0);
    vec3 diffuse = uKd * NdotL;
    vec3 R = reflect(-L, N);
    float spec = NdotL > 0.0 ? pow(max(dot(R, V), 0.0), uShininess) : 0.0;
    vec3 specular = uKs * spec;

    float shadow = 0.0;
    if (uUseShadows == 1) shadow = computeShadow(vPosLight);

    vec3 color = uKa + (1.0 - shadow) * (diffuse + specular);
    color *= uLightColor * uLightIntensity;

    gl_FragColor = vec4(color, uAlpha);
}
""" % (SHADOW_MAP_SIZE)

# -------------------- Shader utils --------------------
def compile_shader(src, stype):
    s = glCreateShader(stype)
    glShaderSource(s, src)
    glCompileShader(s)
    if glGetShaderiv(s, GL_COMPILE_STATUS) != GL_TRUE:
        raise RuntimeError(glGetShaderInfoLog(s).decode())
    return s

def link_program(vs_src, fs_src):
    vs = compile_shader(vs_src, GL_VERTEX_SHADER)
    fs = compile_shader(fs_src, GL_FRAGMENT_SHADER)
    p = glCreateProgram()
    glAttachShader(p, vs); glAttachShader(p, fs)
    glLinkProgram(p)
    if glGetProgramiv(p, GL_LINK_STATUS) != GL_TRUE:
        raise RuntimeError(glGetProgramInfoLog(p).decode())
    glDeleteShader(vs); glDeleteShader(fs)
    return p

# -------------------- Matrices helpers --------------------
def get_matrix(mode):
    arr = (GLfloat * 16)()
    glGetFloatv(mode, arr)
    return np.array(arr, dtype=np.float32).reshape((4,4)).T

def compute_light_vp():
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(60.0, 1.0, 0.5, 60.0)
    light_proj = get_matrix(GL_PROJECTION_MATRIX)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()
    gluLookAt(light_x, light_y, light_z, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    light_view = get_matrix(GL_MODELVIEW_MATRIX)
    return light_proj @ light_view

def begin_camera_view():
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(45.0, window_width / float(window_height), 0.1, 80.0)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()
    cx, cy, cz = apply_camera_rotation()
    gluLookAt(cx, cy, cz, 0, 0, 0, 0, 1, 0)

# -------------------- Shadow FBO --------------------
def create_shadow_fbo():
    global depth_fbo, depth_tex
    depth_fbo = glGenFramebuffers(1)
    glBindFramebuffer(GL_FRAMEBUFFER, depth_fbo)

    depth_tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, depth_tex)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT24, SHADOW_MAP_SIZE, SHADOW_MAP_SIZE, 0,
                 GL_DEPTH_COMPONENT, GL_FLOAT, None)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_BORDER)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_BORDER)
    border = (GLfloat * 4)(1.0, 1.0, 1.0, 1.0)
    glTexParameterfv(GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR, border)

    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, depth_tex, 0)
    glDrawBuffer(GL_NONE); glReadBuffer(GL_NONE)

    status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
    if status != GL_FRAMEBUFFER_COMPLETE:
        raise RuntimeError(f"FBO incomplete: {status}")
    glBindFramebuffer(GL_FRAMEBUFFER, 0)

# -------------------- Raw meshes (no transforms) --------------------
def draw_plane_mesh():
    size = 20.0; y = -1.5
    glBegin(GL_QUADS)
    glNormal3f(0,1,0)
    glVertex3f(-size, y, -size)
    glVertex3f( size, y, -size)
    glVertex3f( size, y,  size)
    glVertex3f(-size, y,  size)
    glEnd()

def draw_icosahedron_mesh():
    glutSolidIcosahedron()

def draw_teapot_mesh():
    glutSolidTeapot(1.5)

def draw_torus_mesh():
    glutSolidTorus(0.5, 1.5, 30, 40)

# -------------------- Helpers --------------------
def draw_axes():
    glUseProgram(0)
    glDisable(GL_LIGHTING)
    glLineWidth(2.0)
    glBegin(GL_LINES)
    glColor3f(1,0,0); glVertex3f(0,0,0); glVertex3f(3,0,0)
    glColor3f(0,1,0); glVertex3f(0,0,0); glVertex3f(0,3,0)
    glColor3f(0,0,1); glVertex3f(0,0,0); glVertex3f(0,0,3)
    glEnd()

def draw_light_marker():
    glUseProgram(0)
    glDisable(GL_LIGHTING)
    glColor3f(1.0, 1.0, 0.0)
    glPushMatrix(); glTranslatef(light_x, light_y, light_z); glutWireSphere(0.2, 10, 10); glPopMatrix()

def set_material(prog, m):
    glUniform3f(glGetUniformLocation(prog, "uKa"), *m["ambient"])
    glUniform3f(glGetUniformLocation(prog, "uKd"), *m["diffuse"])
    glUniform3f(glGetUniformLocation(prog, "uKs"), *m["specular"])
    glUniform1f(glGetUniformLocation(prog, "uShininess"), m["shininess"])
    glUniform1f(glGetUniformLocation(prog, "uAlpha"), m["alpha"])

def set_common_scene_uniforms(prog, light_vp):
    view = get_matrix(GL_MODELVIEW_MATRIX)
    light_world = np.array([light_x, light_y, light_z, 1.0], dtype=np.float32)
    light_eye4 = view @ light_world
    light_eye = (light_eye4[:3] / light_eye4[3]).astype(np.float32)
    view_pos_eye = np.array([0.0, 0.0, 0.0], dtype=np.float32)

    glUniform1i(glGetUniformLocation(prog, "uUseShadows"), 1 if shadow_enabled else 0)
    glUniform1i(glGetUniformLocation(prog, "uUsePCF"), 1 if pcf_enabled else 0)
    glUniform1f(glGetUniformLocation(prog, "uBias"), shadow_bias)
    glUniform3f(glGetUniformLocation(prog, "uLightPosEye"), *light_eye.tolist())
    glUniform3f(glGetUniformLocation(prog, "uViewPosEye"), *view_pos_eye.tolist())
    glUniform3f(glGetUniformLocation(prog, "uLightColor"), *light_color)
    glUniform1f(glGetUniformLocation(prog, "uLightIntensity"), light_intensity)

    glUniformMatrix4fv(glGetUniformLocation(prog, "uLightVP"), 1, GL_TRUE, light_vp.astype(np.float32))

def set_model_uniform_from_current(prog):
    # ModelView = View * Model  =>  Model = inv(View) * ModelView
    modelview = get_matrix(GL_MODELVIEW_MATRIX)
    # Rebuild current View
    cx, cy, cz = apply_camera_rotation()
    glPushMatrix(); glLoadIdentity(); gluLookAt(cx, cy, cz, 0, 0, 0, 0, 1, 0)
    view = get_matrix(GL_MODELVIEW_MATRIX); glPopMatrix()
    inv_view = np.linalg.inv(view)
    model = inv_view @ modelview
    glUniformMatrix4fv(glGetUniformLocation(prog, "uModel"), 1, GL_TRUE, model.astype(np.float32))

# -------------------- Passes --------------------
def render_depth_pass():
    glViewport(0, 0, SHADOW_MAP_SIZE, SHADOW_MAP_SIZE)
    glBindFramebuffer(GL_FRAMEBUFFER, depth_fbo)
    glClear(GL_DEPTH_BUFFER_BIT)

    # Light POV
    glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(60.0, 1.0, 0.5, 60.0)
    glMatrixMode(GL_MODELVIEW);  glLoadIdentity();  gluLookAt(light_x, light_y, light_z, 0, 0, 0, 0, 1, 0)

    glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
    glEnable(GL_CULL_FACE); glCullFace(GL_FRONT)
    glEnable(GL_POLYGON_OFFSET_FILL); glPolygonOffset(1.1, 4.0)

    glUseProgram(prog_depth)

    # Плоскость
    draw_plane_mesh()

    # Тор (должен совпадать со сценой)
    glPushMatrix()
    glTranslatef(2.5, 2.0, 0.0)
    draw_torus_mesh()
    glPopMatrix()

    # Чайник (должен совпадать со сценой)
    glPushMatrix()
    glTranslatef(2.5, 2.0, -3.5)
    draw_teapot_mesh()
    glPopMatrix()

    # Икосаэдр (тот же Y, что и в сцене)
    glPushMatrix()
    glTranslatef(-3.0, 2.0, -0.3)
    glScalef(1.8, 1.8, 1.8)
    draw_icosahedron_mesh()
    glPopMatrix()

    glUseProgram(0)
    glDisable(GL_POLYGON_OFFSET_FILL)
    glCullFace(GL_BACK)
    glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
    glBindFramebuffer(GL_FRAMEBUFFER, 0)

def render_scene_pass(light_vp):
    glViewport(0, 0, window_width, window_height)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    begin_camera_view()

    glUseProgram(prog_scene)
    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_2D, depth_tex)
    glUniform1i(glGetUniformLocation(prog_scene, "uShadowMap"), 0)
    set_common_scene_uniforms(prog_scene, light_vp)

    # Непрозрачные объекты сначала
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)

    # 1) Плоскость пола — отключаем cull только на время её рисования
    set_material(prog_scene, mat_plane)
    glPushMatrix()
    glDisable(GL_CULL_FACE)             # ключ к видимости пола сверху
    set_model_uniform_from_current(prog_scene)
    draw_plane_mesh()
    glEnable(GL_CULL_FACE)              # вернуть как было
    glPopMatrix()

    # 2) Тор
    set_material(prog_scene, mat_torus)
    glPushMatrix()
    glTranslatef(2.5, 2.0, 0.0)
    set_model_uniform_from_current(prog_scene)
    draw_torus_mesh()
    glPopMatrix()

    # 3) Чайник (за тором)
    set_material(prog_scene, mat_teapot)
    glPushMatrix()
    glTranslatef(2.5, 2.0, -3.5)
    set_model_uniform_from_current(prog_scene)
    draw_teapot_mesh()
    glPopMatrix()

    # 4) Икосаэдр — ПРОЗРАЧНЫЙ, рисуем ПОСЛЕДНИМ
    set_material(prog_scene, mat_ico)
    glPushMatrix()
    glTranslatef(-3.0, 2.0, -0.3)
    glScalef(1.8, 1.8, 1.8)

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glDepthMask(GL_FALSE)               # не писать глубину, чтобы прозрачность была настоящей
    glDisable(GL_CULL_FACE)             # видеть обе стороны граней

    set_model_uniform_from_current(prog_scene)
    draw_icosahedron_mesh()

    glEnable(GL_CULL_FACE)
    glDepthMask(GL_TRUE)
    glDisable(GL_BLEND)

    glPopMatrix()

    glUseProgram(0)
    draw_axes()
    draw_light_marker()

def draw_text(x, y, text):
    glUseProgram(0)
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, window_width, 0, window_height)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glColor3f(1,1,1); glRasterPos2f(x, y)
    for ch in text: glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(ch))
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)

# -------------------- GLUT callbacks --------------------
def display():
    light_vp = compute_light_vp()
    render_depth_pass()
    render_scene_pass(light_vp)

    draw_text(20, window_height - 30, "Lab 3: Shadow Mapping")
    draw_text(20, window_height - 50, f"Light: [{light_x:.1f}, {light_y:.1f}, {light_z:.1f}]  Intensity: {light_intensity:.2f}")
    draw_text(20, window_height - 70, f"Color: RGB({light_color[0]:.1f}, {light_color[1]:.1f}, {light_color[2]:.1f})")
    draw_text(20, window_height - 90, f"Shadows: {'ON' if shadow_enabled else 'OFF'}  PCF: {'ON' if pcf_enabled else 'OFF'}  Bias: {shadow_bias:.4f}")
    draw_text(20, 60, "Objects: Torus (front), Teapot (behind), Icosahedron (left), Floor plane")
    draw_text(20, 40, "Keys: Camera(LMB/Scroll/R), Light(WASDQE,+/-), Color(1-5), Shadows(O), PCF(P), Bias([,])")
    glutSwapBuffers()

def reshape(w, h):
    global window_width, window_height
    window_width = max(1, w); window_height = max(1, h)
    glViewport(0, 0, window_width, window_height)

def keyboard(key, x, y):
    global rotation_x, rotation_y, zoom
    global light_x, light_y, light_z, light_intensity, light_color
    global shadow_enabled, pcf_enabled, shadow_bias

    if key in (b'r', b'R'):
        rotation_x = 30.0; rotation_y = 45.0; zoom = 1.0
    elif key in (b'+', b'='):
        light_intensity = min(2.0, light_intensity + 0.1)
    elif key in (b'-', b'_'):
        light_intensity = max(0.0, light_intensity - 0.1)
    elif key in (b'w', b'W'):
        light_y += 0.5
    elif key in (b's', b'S'):
        light_y -= 0.5
    elif key in (b'a', b'A'):
        light_x -= 0.5
    elif key in (b'd', b'D'):
        light_x += 0.5
    elif key in (b'q', b'Q'):
        light_z += 0.5
    elif key in (b'e', b'E'):
        light_z -= 0.5
    elif key == b'1':
        light_color = [1.0, 0.0, 0.0]
    elif key == b'2':
        light_color = [0.0, 1.0, 0.0]
    elif key == b'3':
        light_color = [0.0, 0.0, 1.0]
    elif key == b'4':
        light_color = [1.0, 1.0, 0.0]
    elif key == b'5':
        light_color = [1.0, 1.0, 1.0]
    elif key in (b'o', b'O'):
        shadow_enabled = not shadow_enabled
    elif key in (b'p', b'P'):
        pcf_enabled = not pcf_enabled
    elif key == b'[':
        shadow_bias = max(0.0, shadow_bias - 0.0005)
    elif key == b']':
        shadow_bias = min(0.05, shadow_bias + 0.0005)
    elif key == b'\x1b':
        sys.exit(0)
    elif key == b'7':
        # Тор ближе к свету по направлению +Z -> его тень падает на чайник
        light_x, light_y, light_z = 6.0, 8.0, 3.0
        print("Preset 7: Torus -> Teapot shadow")
    elif key == b'8':
        # Чайник ближе к свету по направлению -Z -> его тень падает на тор
        light_x, light_y, light_z = 6.0, 8.0, -7.0
        print("Preset 8: Teapot -> Torus shadow")
    glutPostRedisplay()

def mouse(button, state, x, y):
    global mouse_down, mouse_x, mouse_y, zoom
    if button == GLUT_LEFT_BUTTON:
        if state == GLUT_DOWN:
            mouse_down = True; mouse_x = x; mouse_y = y
        else:
            mouse_down = False
    elif button == 3:
        zoom *= 0.9; glutPostRedisplay()
    elif button == 4:
        zoom *= 1.1; glutPostRedisplay()

def motion(x, y):
    global mouse_x, mouse_y, rotation_x, rotation_y
    if mouse_down:
        dx = x - mouse_x; dy = y - mouse_y
        rotation_y += dx * 0.5
        rotation_x += dy * 0.5
        rotation_x = max(-89.0, min(89.0, rotation_x))
        mouse_x = x; mouse_y = y
        glutPostRedisplay()

def init_opengl():
    glClearColor(0.18, 0.19, 0.22, 1.0)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_MULTISAMPLE)

    global prog_depth, prog_scene
    prog_depth = link_program(vs_depth, fs_depth)
    prog_scene = link_program(vs_scene, fs_scene)

    create_shadow_fbo()

def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH | GLUT_MULTISAMPLE)
    glutInitWindowSize(window_width, window_height)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Lab 3: Shadow Mapping (Torus front, Teapot behind)")

    init_opengl()
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)
    glutMouseFunc(mouse)
    glutMotionFunc(motion)

    print("="*80)
    print("ЛАБА 3: Динамические тени (shadow mapping). Тор спереди, чайник позади, пол-плоскость")
    print("Клавиши: ЛКМ/колесо/R; W/A/S/D/Q/E; +/-; 1-5; O; P; [; ]")
    print("="*80)

    glutMainLoop()

if __name__ == "__main__":
    main()
