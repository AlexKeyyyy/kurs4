from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import sys
import numpy as np
from PIL import Image

window_width = 1200
window_height = 800
current_task = 1
screenshot_taken = [False, False, False, False]

mouse_down = False
mouse_x = 0
mouse_y = 0
rotation_x = 30.0
rotation_y = 45.0
zoom = 1.0

def init_opengl():
    """Инициализация параметров OpenGL"""
    glClearColor(1.0, 1.0, 1.0, 1.0)
    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, window_width / window_height, 0.1, 50.0)
    glMatrixMode(GL_MODELVIEW)

def draw_axes():
    """Отрисовка осей координат X, Y, Z"""
    glLineWidth(2.0)

    # Ось X (красная)
    glColor3f(1.0, 0.0, 0.0)
    glBegin(GL_LINES)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(3.0, 0.0, 0.0)
    glEnd()

    # Ось Y (зеленая)
    glColor3f(0.0, 1.0, 0.0)
    glBegin(GL_LINES)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(0.0, 3.0, 0.0)
    glEnd()

    # Ось Z (синяя)
    glColor3f(0.0, 0.0, 1.0)
    glBegin(GL_LINES)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(0.0, 0.0, 3.0)
    glEnd()

def draw_text(x, y, text):
    glDisable(GL_DEPTH_TEST)

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, window_width, 0, window_height)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glColor3f(0.0, 0.0, 0.0)
    glRasterPos2f(x, y)
    for char in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()

    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)

def save_screenshot(filename):
    glReadBuffer(GL_FRONT)
    pixels = glReadPixels(0, 0, window_width, window_height, GL_RGB, GL_UNSIGNED_BYTE)
    image = Image.frombytes("RGB", (window_width, window_height), pixels)
    image = image.transpose(Image.FLIP_TOP_BOTTOM)
    image.save(filename)
    print(f"✓ Сохранено изображение: {filename}")

def apply_camera_rotation():
    """Применение вращения камеры на основе позиции мыши"""
    distance = 10.0 * zoom

    rot_x_rad = np.radians(rotation_x)
    rot_y_rad = np.radians(rotation_y)

    cam_x = distance * np.sin(rot_y_rad) * np.cos(rot_x_rad)
    cam_y = distance * np.sin(rot_x_rad)
    cam_z = distance * np.cos(rot_y_rad) * np.cos(rot_x_rad)

    return cam_x, cam_y, cam_z

def display_task_1():
    """ЗАДАНИЕ 1: Каркасный икосаэдр и каркасный конус на одной плоскости"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    cam_x, cam_y, cam_z = apply_camera_rotation()
    gluLookAt(cam_x, cam_y, cam_z, 0, 0, 0, 0, 1, 0)

    draw_axes()

    # Икосаэдр слева
    glPushMatrix()
    glTranslatef(-2.5, 0.0, 0.0)
    glColor3f(0.0, 0.0, 1.0)
    glScalef(1.5, 1.5, 1.5)
    glutWireIcosahedron()
    glPopMatrix()

    # Конус справа
    glPushMatrix()
    glTranslatef(2.5, 0.0, 0.0)
    glColor3f(1.0, 0.0, 0.0)
    glutWireCone(1.2, 2.5, 20, 20)
    glPopMatrix()

    draw_text(20, window_height - 30, "TASK 1: Icosahedron and Cone")

    glutSwapBuffers()

    global screenshot_taken
    if not screenshot_taken[0]:
        save_screenshot("zadanie_1_opengl.png")
        screenshot_taken[0] = True

def display_task_2():
    """ЗАДАНИЕ 2: Поворот конуса на -60° вокруг оси X, сдвиг икосаэдра по Z"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    cam_x, cam_y, cam_z = apply_camera_rotation()
    gluLookAt(cam_x, cam_y, cam_z, 0, 0, 0, 0, 1, 0)

    draw_axes()

    # Икосаэдр со сдвигом по Z
    glPushMatrix()
    glTranslatef(-2.5, 0.0, 3.0)  # Сдвиг по Z на 3.0
    glColor3f(0.0, 0.0, 1.0)
    glScalef(1.5, 1.5, 1.5)
    glutWireIcosahedron()
    glPopMatrix()

    # Конус с поворотом на -60° вокруг оси X
    glPushMatrix()
    glTranslatef(2.5, 0.0, 0.0)
    glRotatef(-60.0, 1.0, 0.0, 0.0)  # Поворот на -60° вокруг оси X
    glColor3f(1.0, 0.0, 0.0)
    glutWireCone(1.2, 2.5, 20, 20)
    glPopMatrix()

    draw_text(20, window_height - 30, "TASK 2: Rotated Cone (-60 X) and Shifted Icosahedron (Z+3)")

    glutSwapBuffers()

    global screenshot_taken
    if not screenshot_taken[1]:
        save_screenshot("zadanie_2_opengl.png")
        screenshot_taken[1] = True

def display_task_3():
    """ЗАДАНИЕ 3: Каркасный чайник и каркасный тор на одной плоскости"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    cam_x, cam_y, cam_z = apply_camera_rotation()
    gluLookAt(cam_x, cam_y, cam_z, 0, 0, 0, 0, 1, 0)

    draw_axes()

    # Чайник слева
    glPushMatrix()
    glTranslatef(-2.5, -0.5, 0.0)
    glColor3f(0.0, 0.5, 0.0)
    glutWireTeapot(1.2)
    glPopMatrix()

    # Тор справа
    glPushMatrix()
    glTranslatef(2.5, 0.0, 0.0)
    glColor3f(0.5, 0.0, 0.5)
    glutWireTorus(0.5, 1.5, 20, 30)
    glPopMatrix()

    draw_text(20, window_height - 30, "TASK 3: Teapot and Torus")

    glutSwapBuffers()

    global screenshot_taken
    if not screenshot_taken[2]:
        save_screenshot("zadanie_3_opengl.png")
        screenshot_taken[2] = True

def display_task_4():
    """ЗАДАНИЕ 4: Чайник и тор с коэффициентом масштабирования 0.5"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    cam_x, cam_y, cam_z = apply_camera_rotation()
    gluLookAt(cam_x, cam_y, cam_z, 0, 0, 0, 0, 1, 0)

    draw_axes()

    # Чайник слева (без изменений)
    glPushMatrix()
    glTranslatef(-2.5, -0.5, 0.0)
    glColor3f(0.0, 0.5, 0.0)
    glutWireTeapot(1.2)
    glPopMatrix()

    # Тор справа с масштабированием 0.5
    glPushMatrix()
    glTranslatef(2.5, 0.0, 0.0)
    glScalef(0.5, 0.5, 0.5)  # Масштабирование с коэффициентом 0.5
    glColor3f(1.0, 0.5, 0.0)
    glutWireTorus(0.5, 1.5, 20, 30)
    glPopMatrix()

    draw_text(20, window_height - 30, "TASK 4: Teapot and Scaled Torus (scale 0.5)")

    glutSwapBuffers()

    global screenshot_taken
    if not screenshot_taken[3]:
        save_screenshot("zadanie_4_opengl.png")
        screenshot_taken[3] = True
        print("\n" + "="*70)
        print("✓ ВСЕ ИЗОБРАЖЕНИЯ СОХРАНЕНЫ!")
        print("="*70)

def display():
    """Основная функция отображения"""
    if current_task == 1:
        display_task_1()
    elif current_task == 2:
        display_task_2()
    elif current_task == 3:
        display_task_3()
    elif current_task == 4:
        display_task_4()

def keyboard(key, x, y):
    """Обработка нажатий клавиш"""
    global current_task, rotation_x, rotation_y, zoom

    if key == b'1':
        current_task = 1
        glutPostRedisplay()
    elif key == b'2':
        current_task = 2
        glutPostRedisplay()
    elif key == b'3':
        current_task = 3
        glutPostRedisplay()
    elif key == b'4':
        current_task = 4
        glutPostRedisplay()
    elif key == b's':
        save_screenshot(f"screenshot_task_{current_task}.png")
    elif key == b'r':
        rotation_x = 30.0
        rotation_y = 45.0
        zoom = 1.0
        glutPostRedisplay()
        print("Вращение сброшено к начальным значениям")
    elif key == b'\x1b':  # ESC
        sys.exit(0)

def mouse(button, state, x, y):
    """Обработка нажатий кнопок мыши"""
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
    """Обработка движения мыши с нажатой кнопкой"""
    global mouse_x, mouse_y, rotation_x, rotation_y

    if mouse_down:
        dx = x - mouse_x
        dy = y - mouse_y

        rotation_y += dx * 0.5
        rotation_x += dy * 0.5

        if rotation_x > 89.0:
            rotation_x = 89.0
        if rotation_x < -89.0:
            rotation_x = -89.0

        mouse_x = x
        mouse_y = y

        glutPostRedisplay()

def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(window_width, window_height)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Lab1: OpenGL - Interactive")

    init_opengl()

    glutDisplayFunc(display)
    glutKeyboardFunc(keyboard)
    glutMouseFunc(mouse)
    glutMotionFunc(motion)

    print("="*70)
    print("Лабораторная работа 1 - Исправленная версия")
    print("="*70)
    print("\nУправление клавиатурой:")
    print("  '1' - Задание 1: Икосаэдр и конус")
    print("  '2' - Задание 2: Трансформации")
    print("  '3' - Задание 3: Чайник и тор")
    print("  '4' - Задание 4: Масштабирование тора")
    print("  'S' - Сохранить текущий кадр")
    print("  'R' - Сбросить вращение к начальным значениям")
    print("  'ESC' - Выход")
    print("\nУправление мышью:")
    print("  ЛКМ + движение мыши - Вращение сцены")
    print("  Колесико мыши - Приближение/отдаление (зум)")
    print("="*70)
    print("\nИзображения будут автоматически сохранены при переключении заданий.")
    print("="*70)

    glutMainLoop()

if __name__ == "__main__":
    main()
