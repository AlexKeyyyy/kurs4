from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import sys
import numpy as np
from PIL import Image

window_width = 1400
window_height = 900

# Управление камерой
mouse_down = False
mouse_x = 0
mouse_y = 0
rotation_x = 30.0
rotation_y = 45.0
zoom = 1.0

# Управление источником света
light_x = 5.0
light_y = 5.0
light_z = 5.0
light_intensity = 1.0
light_color = [1.0, 1.0, 1.0]

# Текстура
texture_id = None
use_texture = True


def create_procedural_texture():
    """Создание процедурной текстуры (шахматная доска)"""
    width, height = 256, 256
    data = np.zeros((height, width, 3), dtype=np.uint8)

    square_size = 32
    for i in range(height):
        for j in range(width):
            if ((i // square_size) + (j // square_size)) % 2 == 0:
                data[i, j] = [255, 200, 100]
            else:
                data[i, j] = [50, 50, 150]

    return data


def load_texture():
    """Загрузка текстуры"""
    global texture_id
    texture_data = create_procedural_texture()
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 256, 256, 0,
                 GL_RGB, GL_UNSIGNED_BYTE, texture_data)
    glBindTexture(GL_TEXTURE_2D, 0)
    print("✓ Текстура загружена")


def init_opengl():
    """Инициализация параметров OpenGL"""
    glClearColor(0.1, 0.1, 0.15, 1.0)
    glEnable(GL_DEPTH_TEST)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, window_width / window_height, 0.1, 50.0)
    glMatrixMode(GL_MODELVIEW)

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)

    # Прозрачность
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    load_texture()
    print("✓ OpenGL инициализирован")


def setup_light():
    """Настройка источника освещения"""
    light_position = [light_x, light_y, light_z, 1.0]
    glLightfv(GL_LIGHT0, GL_POSITION, light_position)

    ambient = [0.2 * light_intensity, 0.2 * light_intensity, 0.2 * light_intensity, 1.0]
    diffuse = [light_color[0] * light_intensity,
               light_color[1] * light_intensity,
               light_color[2] * light_intensity, 1.0]
    specular = [1.0, 1.0, 1.0, 1.0]

    glLightfv(GL_LIGHT0, GL_AMBIENT, ambient)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, diffuse)
    glLightfv(GL_LIGHT0, GL_SPECULAR, specular)


def draw_light_marker():
    """Отрисовка маркера источника света"""
    glDisable(GL_LIGHTING)
    glDisable(GL_TEXTURE_2D)
    glColor3f(1.0, 1.0, 0.0)
    glPushMatrix()
    glTranslatef(light_x, light_y, light_z)
    glutWireSphere(0.2, 10, 10)
    glPopMatrix()
    glEnable(GL_LIGHTING)


def draw_axes():
    """Отрисовка осей координат"""
    glDisable(GL_LIGHTING)
    glDisable(GL_TEXTURE_2D)
    glLineWidth(2.0)

    glColor3f(1.0, 0.0, 0.0)
    glBegin(GL_LINES)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(3.0, 0.0, 0.0)
    glEnd()

    glColor3f(0.0, 1.0, 0.0)
    glBegin(GL_LINES)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(0.0, 3.0, 0.0)
    glEnd()

    glColor3f(0.0, 0.0, 1.0)
    glBegin(GL_LINES)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(0.0, 0.0, 3.0)
    glEnd()

    glEnable(GL_LIGHTING)


def draw_transparent_icosahedron():
    """ОБЪЕКТ 1: Прозрачный икосаэдр (alpha = 0.3)"""
    glDepthMask(GL_FALSE)

    # СИЛЬНО ПРОЗРАЧНЫЙ (alpha = 0.3)
    ambient = [0.1, 0.4, 0.7, 0.3]
    diffuse = [0.2, 0.6, 1.0, 0.3]
    specular = [0.5, 0.5, 0.8, 0.3]
    shininess = [30.0]

    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, ambient)
    glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, diffuse)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, specular)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SHININESS, shininess)

    glPushMatrix()
    glTranslatef(-4.0, 0.0, 0.0)
    glScalef(1.8, 1.8, 1.8)
    glutSolidIcosahedron()
    glPopMatrix()

    glDepthMask(GL_TRUE)


def draw_polished_teapot():
    """ОБЪЕКТ 2: Отполированный чайник за икосаэдром"""
    ambient = [0.25, 0.0, 0.25, 1.0]
    diffuse = [1.0, 0.0, 1.0, 1.0]
    specular = [1.0, 1.0, 1.0, 1.0]
    shininess = [128.0]

    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, ambient)
    glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, diffuse)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, specular)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SHININESS, shininess)

    glPushMatrix()
    glTranslatef(-4.0, 0.0, -3.0)  # За икосаэдром
    glutSolidTeapot(1.5)
    glPopMatrix()


def draw_textured_torus():
    """ОБЪЕКТ 3: Матовый тор с текстурой"""
    ambient = [0.3, 0.3, 0.3, 1.0]
    diffuse = [0.8, 0.8, 0.8, 1.0]
    specular = [0.1, 0.1, 0.1, 1.0]
    shininess = [5.0]

    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, ambient)
    glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, diffuse)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, specular)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SHININESS, shininess)

    if use_texture and texture_id:
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
        glEnable(GL_TEXTURE_GEN_S)
        glEnable(GL_TEXTURE_GEN_T)
        glTexGeni(GL_S, GL_TEXTURE_GEN_MODE, GL_OBJECT_LINEAR)
        glTexGeni(GL_T, GL_TEXTURE_GEN_MODE, GL_OBJECT_LINEAR)

    glPushMatrix()
    glTranslatef(4.0, 0.0, 0.0)
    glutSolidTorus(0.5, 1.5, 30, 40)
    glPopMatrix()

    if use_texture:
        glDisable(GL_TEXTURE_GEN_S)
        glDisable(GL_TEXTURE_GEN_T)
        glDisable(GL_TEXTURE_2D)


def draw_text(x, y, text):
    """Отрисовка текста на экране"""
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glDisable(GL_TEXTURE_2D)

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, window_width, 0, window_height)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glColor3f(1.0, 1.0, 1.0)
    glRasterPos2f(x, y)
    for char in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(char))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)


def apply_camera_rotation():
    """Применение вращения камеры"""
    distance = 12.0 * zoom
    rot_x_rad = np.radians(rotation_x)
    rot_y_rad = np.radians(rotation_y)
    cam_x = distance * np.sin(rot_y_rad) * np.cos(rot_x_rad)
    cam_y = distance * np.sin(rot_x_rad)
    cam_z = distance * np.cos(rot_y_rad) * np.cos(rot_x_rad)
    return cam_x, cam_y, cam_z


def display():
    """Основная функция отображения"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    cam_x, cam_y, cam_z = apply_camera_rotation()
    gluLookAt(cam_x, cam_y, cam_z, 0, 0, 0, 0, 1, 0)

    setup_light()
    draw_axes()
    draw_light_marker()

    # ПОРЯДОК: непрозрачные → прозрачные
    draw_textured_torus()
    draw_polished_teapot()  # За икосаэдром
    draw_transparent_icosahedron()  # Прозрачный последним!

    draw_text(20, window_height - 30, "Lab 2: Materials, Lighting, Textures")
    draw_text(20, window_height - 50, f"Light: [{light_x:.1f}, {light_y:.1f}, {light_z:.1f}]")
    draw_text(20, window_height - 70, f"Intensity: {light_intensity:.2f}")
    draw_text(20, window_height - 90, f"Color: RGB({light_color[0]:.1f}, {light_color[1]:.1f}, {light_color[2]:.1f})")
    draw_text(20, window_height - 110, f"Texture: {'ON' if use_texture else 'OFF'}")
    draw_text(20, 120, "Objects:")
    draw_text(20, 100, "  Left: TRANSPARENT Icosahedron (alpha=0.3) - SEE TEAPOT BEHIND!")
    draw_text(20, 80, "  Behind: Polished PURPLE Teapot (shininess=128)")
    draw_text(20, 60, "  Right: Matte Textured Torus (shininess=5)")
    draw_text(20, 40, "Press 'H' for help")

    glutSwapBuffers()


def keyboard(key, x, y):
    """Обработка нажатий клавиш"""
    global rotation_x, rotation_y, zoom, light_intensity, light_color, use_texture
    global light_x, light_y, light_z

    if key == b'r' or key == b'R':
        rotation_x = 30.0
        rotation_y = 45.0
        zoom = 1.0
        print("Камера сброшена")
    elif key == b'+' or key == b'=':
        light_intensity = min(2.0, light_intensity + 0.1)
        print(f"Интенсивность: {light_intensity:.2f}")
    elif key == b'-' or key == b'_':
        light_intensity = max(0.0, light_intensity - 0.1)
        print(f"Интенсивность: {light_intensity:.2f}")
    elif key == b'w' or key == b'W':
        light_y += 0.5
        print(f"Свет Y={light_y:.1f}")
    elif key == b's' or key == b'S':
        light_y -= 0.5
        print(f"Свет Y={light_y:.1f}")
    elif key == b'a' or key == b'A':
        light_x -= 0.5
        print(f"Свет X={light_x:.1f}")
    elif key == b'd' or key == b'D':
        light_x += 0.5
        print(f"Свет X={light_x:.1f}")
    elif key == b'q' or key == b'Q':
        light_z += 0.5
        print(f"Свет Z={light_z:.1f}")
    elif key == b'e' or key == b'E':
        light_z -= 0.5
        print(f"Свет Z={light_z:.1f}")
    elif key == b'1':
        light_color = [1.0, 0.0, 0.0]
        print("Свет: Красный")
    elif key == b'2':
        light_color = [0.0, 1.0, 0.0]
        print("Свет: Зелёный")
    elif key == b'3':
        light_color = [0.0, 0.0, 1.0]
        print("Свет: Синий")
    elif key == b'4':
        light_color = [1.0, 1.0, 0.0]
        print("Свет: Жёлтый")
    elif key == b'5':
        light_color = [1.0, 1.0, 1.0]
        print("Свет: Белый")
    elif key == b't' or key == b'T':
        use_texture = not use_texture
        print(f"Текстура: {'ВКЛ' if use_texture else 'ВЫКЛ'}")
    elif key == b'h' or key == b'H':
        print("\n" + "=" * 80)
        print("УПРАВЛЕНИЕ")
        print("=" * 80)
        print("Камера: ЛКМ+движение, колесико, R")
        print("Свет: W/A/S/D/Q/E (позиция), +/- (интенсивность), 1-5 (цвет)")
        print("Текстура: T")
        print("=" * 80 + "\n")
    elif key == b'\x1b':
        sys.exit(0)

    glutPostRedisplay()


def mouse(button, state, x, y):
    """Обработка мыши"""
    global mouse_down, mouse_x, mouse_y, zoom

    if button == GLUT_LEFT_BUTTON:
        if state == GLUT_DOWN:
            mouse_down = True
            mouse_x = x
            mouse_y = y
        else:
            mouse_down = False
    elif button == 3:
        zoom *= 0.9
        glutPostRedisplay()
    elif button == 4:
        zoom *= 1.1
        glutPostRedisplay()


def motion(x, y):
    """Движение мыши"""
    global mouse_x, mouse_y, rotation_x, rotation_y

    if mouse_down:
        dx = x - mouse_x
        dy = y - mouse_y
        rotation_y += dx * 0.5
        rotation_x += dy * 0.5
        rotation_x = max(-89.0, min(89.0, rotation_x))
        mouse_x = x
        mouse_y = y
        glutPostRedisplay()


def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH | GLUT_ALPHA)
    glutInitWindowSize(window_width, window_height)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Lab 2: Materials, Lighting, Textures")

    init_opengl()
    glutDisplayFunc(display)
    glutKeyboardFunc(keyboard)
    glutMouseFunc(mouse)
    glutMotionFunc(motion)

    print("=" * 80)
    print("ЛАБА 2: Материалы, Освещение, Текстуры")
    print("=" * 80)
    print("\n✓ Вариант #10: икосаэдр, конус, чайник, тор")
    print("\n✓ ОБЪЕКТЫ:")
    print("  1. Икосаэдр (слева)  - ПРОЗРАЧНЫЙ (alpha=0.3)")
    print("  2. Чайник (за ним)   - Отполированный (shininess=128)")
    print("  3. Тор (справа)      - Матовый текстурированный")
    print("\n✓ Освещение: точечный источник (W/A/S/D/Q/E, +/-, 1-5)")
    print("✓ Текстура: процедурная шахматная доска (T)")
    print("=" * 80)

    glutMainLoop()


if __name__ == "__main__":
    main()
