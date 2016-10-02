#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" This program demonstrates the use of pyassimp to load and
render objects with OpenGL.

'c' cycles between cameras (if any available)
'q' to quit

This example mixes 'old' OpenGL fixed-function pipeline with 
Vertex Buffer Objects.

Materials are supported but textures are currently ignored.

For a more advanced example (with shaders + keyboard/mouse 
controls), check scripts/sdl_viewer.py

Author: SÃ©verin Lemaignan, 2012

This sample is based on several sources, including:
 - http://www.lighthouse3d.com/tutorials
 - http://www.songho.ca/opengl/gl_transform.html
 - http://code.activestate.com/recipes/325391/
 - ASSIMP's C++ SimpleOpenGL viewer
"""

import os, sys
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GL import *

import argparse
import asciiTools
import math
import numpy
import curses

import pyassimp
from pyassimp.postprocess import *
from pyassimp.helper import *
from PIL import Image

name = 'pyassimp OpenGL viewer'
waitTime = 0  # Time to wait between frames
rotating = False
cameraVals = [[0, 0, 0],
              [0, 0, 0],
              [0, 1, 0]]
phi = 0
theta = 0
radius = 0
data = None


class GLRenderer():
    def __init__(self):

        self.scene = None

        self.using_fixed_cam = False
        self.current_cam_index = 0

        # store the global scene rotation
        self.angle = 0.

        # for FPS calculation
        self.prev_time = 0
        self.prev_fps_time = 0
        self.frames = 0
        self.prev_refreshed_time = 0

    def prepare_gl_buffers(self, mesh):
        """ Creates 3 buffer objets for each mesh, 
        to store the vertices, the normals, and the faces
        indices.
        """

        mesh.gl = {}

        # Fill the buffer for vertex positions
        mesh.gl["vertices"] = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, mesh.gl["vertices"])
        glBufferData(GL_ARRAY_BUFFER, 
                    mesh.vertices,
                    GL_STATIC_DRAW)

        # Fill the buffer for normals
        mesh.gl["normals"] = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, mesh.gl["normals"])
        glBufferData(GL_ARRAY_BUFFER, 
                    mesh.normals,
                    GL_STATIC_DRAW)


        # Fill the buffer for vertex positions
        mesh.gl["triangles"] = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, mesh.gl["triangles"])
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, 
                    mesh.faces,
                    GL_STATIC_DRAW)

        # Unbind buffers
        glBindBuffer(GL_ARRAY_BUFFER,0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,0)

    def load_model(self, path, postprocess = None):
        if postprocess:
            self.scene = pyassimp.load(path, postprocess)
        else:
            self.scene = pyassimp.load(path)

        scene = self.scene
        self.bb_min, self.bb_max = get_bounding_box(self.scene)
        self.scene_center = [(a + b) / 2. for a, b in zip(self.bb_min, self.bb_max)]

        for index, mesh in enumerate(scene.meshes):
            self.prepare_gl_buffers(mesh)

        # Finally release the model
        pyassimp.release(scene)

    def cycle_cameras(self):
        self.current_cam_index
        if not self.scene.cameras:
            return None
        self.current_cam_index = (self.current_cam_index + 1) % len(self.scene.cameras)
        cam = self.scene.cameras[self.current_cam_index]
        return cam

    def set_default_camera(self):
        global phi, theta
        theta = 0
        phi = 0
        if not self.using_fixed_cam:
            glLoadIdentity()
            gluLookAt(0.,0.,3.,
                      0.,0.,-5.,
                      0.,1.,0.)

    def fit_scene(self, restore = False):
        """ Compute a scale factor and a translation to fit and center
        the whole geometry on the screen.
        """

        x_max = self.bb_max[0] - self.bb_min[0]
        y_max = self.bb_max[1] - self.bb_min[1]
        tmp = max(x_max, y_max)
        z_max = self.bb_max[2] - self.bb_min[2]
        tmp = max(z_max, tmp)

        if not restore:
            tmp = 1. / tmp

        glScalef(tmp, tmp, tmp)

        # center the model
        direction = -1 if not restore else 1
        glTranslatef( direction * self.scene_center[0], 
                      direction * self.scene_center[1], 
                      direction * self.scene_center[2] )
        cameraVals[1][0] = self.scene_center[0]
        cameraVals[1][1] = self.scene_center[1]
        cameraVals[1][2] = self.scene_center[2]
#        self.calcRadiusToObject()
        return x_max, y_max, z_max

    def apply_material(self, mat):
        """ Apply an OpenGL, using one OpenGL display list per material to cache 
        the operation.
        """

        if not hasattr(mat, "gl_mat"): # evaluate once the mat properties, and cache the values in a glDisplayList.
            diffuse = numpy.array(mat.properties.get("diffuse", [0.8, 0.8, 0.8, 1.0]))
            specular = numpy.array(mat.properties.get("specular", [0., 0., 0., 1.0]))
            ambient = numpy.array(mat.properties.get("ambient", [0.2, 0.2, 0.2, 1.0]))
            emissive = numpy.array(mat.properties.get("emissive", [0., 0., 0., 1.0]))
            shininess = min(mat.properties.get("shininess", 1.0), 128)
            wireframe = mat.properties.get("wireframe", 0)
            twosided = mat.properties.get("twosided", 1)

            setattr(mat, "gl_mat", glGenLists(1))
            glNewList(mat.gl_mat, GL_COMPILE)
    
            glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, diffuse)
            glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, specular)
            glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, ambient)
            glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, emissive)
            glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, shininess)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if wireframe else GL_FILL)
            glDisable(GL_CULL_FACE) if twosided else glEnable(GL_CULL_FACE)

            glEndList()

        glCallList(mat.gl_mat)

    def do_motion(self):
        gl_time = glutGet(GLUT_ELAPSED_TIME)
        self.angle = (gl_time - self.prev_time) * 0.1
        self.prev_time = gl_time
        
        # Compute FPS
        self.frames += 1
        if gl_time - self.prev_fps_time >= 1000:
            current_fps = self.frames * 1000 / (gl_time - self.prev_fps_time)
            self.frames = 0
            self.prev_fps_time = gl_time

    def recursive_render(self, node):
        """ Main recursive rendering method.
        """

        # save model matrix and apply node transformation
        glPushMatrix()
        m = node.transformation.transpose() # OpenGL row major
        glMultMatrixf(m)

        for mesh in node.meshes:
            self.apply_material(mesh.material)

            glBindBuffer(GL_ARRAY_BUFFER, mesh.gl["vertices"])
            glEnableClientState(GL_VERTEX_ARRAY)
            glVertexPointer(3, GL_FLOAT, 0, None)

            glBindBuffer(GL_ARRAY_BUFFER, mesh.gl["normals"])
            glEnableClientState(GL_NORMAL_ARRAY)
            glNormalPointer(GL_FLOAT, 0, None)

            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, mesh.gl["triangles"])
            glDrawElements(GL_TRIANGLES,len(mesh.faces) * 3, GL_UNSIGNED_INT, None)

            glDisableClientState(GL_VERTEX_ARRAY)
            glDisableClientState(GL_NORMAL_ARRAY)

            glBindBuffer(GL_ARRAY_BUFFER, 0)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

        for child in node.children:
            self.recursive_render(child)

        glPopMatrix()

    def display(self):
        """ GLUT callback to redraw OpenGL surface
        """
        global data
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        self.recursive_render(self.scene.rootnode)
        # glFlush()
        # glutSwapBuffers()
        if rotating:
            self.do_motion()
            data = None
        self.checkInput()
        glRotatef(self.angle,0.,1.,0.)
        self.angle = 0
#        self.rotateCamera(0, 0)
        if data is None:
            data = glReadPixels(0, 0, width * 2, height, GL_RGB, GL_UNSIGNED_BYTE, outputType=None)
            displayData(data)
        glutPostRedisplay()
        return

    def checkInput(self):
        global radius, data
        c = curseScreen.getch()
        if c == -1:
            return
        data = None
        if c == ord('k'):
            killApp()
            sys.exit(0)
        elif c == ord('r'):
            global rotating
            rotating = not rotating
        elif c == ord('t'):
            self.set_default_camera()
        elif c == ord('g'):
           self.fit_scene()
        elif c == ord('w'):
            glTranslatef(0, 1, 0)
        elif c == ord('s'):
            glTranslatef(0, -1, 0)
        elif c == ord('a'):
            glTranslatef(-1, 0, 0)
        elif c == ord('d'):
            glTranslatef(1, 0, 0)
        elif c == curses.KEY_DOWN:
            glScalef(.9, .9, .9)
        elif c == curses.KEY_UP:
            glScalef(1.1, 1.1, 1.1)
        elif c == curses.KEY_LEFT:
            self.angle -= 10
        elif c == curses.KEY_RIGHT:
            self.angle += 10


    def calcRadiusToObject(self):
        global radius
#        radius = 5
        radius = math.sqrt((cameraVals[0][0] - cameraVals[1][0]) ** 2
                           + (cameraVals[0][1] - cameraVals[1][1]) ** 2
                           + (cameraVals[0][2] - cameraVals[1][2]) ** 2)

    def rotateCamera(self, phiDelta, thetaDelta):
        global radius
        phi = phiDelta
        theta = thetaDelta

        eyeX = cameraVals[1][0] + radius * math.cos(phi) * math.sin(theta)
        eyeY = cameraVals[1][1] + radius * math.sin(phi) * math.sin(theta)
        eyeZ = cameraVals[1][2] + radius * math.cos(theta)
        gluLookAt(eyeX, eyeY, eyeZ, cameraVals[1][0], cameraVals[1][1], cameraVals[1][2], 0, 1, 0)
        self.calcRadiusToObject()


    def moveCamera(self, ex=0, ey=0, ez=0, cx=0, cy=0, cz=0, upx=0, upy=0, upz=0):
        cameraVals[0][0] += ex
        cameraVals[0][1] += ey
        cameraVals[0][2] += ez
        cameraVals[1][0] += cx        
        cameraVals[1][1] += cy
        cameraVals[1][2] += cz
        cameraVals[2][0] += upx
        cameraVals[2][1] += upy
        cameraVals[2][2] += upz
        gluLookAt(cameraVals[0][0], cameraVals[0][1], cameraVals[0][2],
                  cameraVals[1][0], cameraVals[1][1], cameraVals[1][2],
                  cameraVals[2][0], cameraVals[2][1], cameraVals[2][2])
        

    # This doesn't do anything because
    def onkeypress(self, key, x, y):
        return

    def render(self, filename=None, fullscreen = False, autofit = True, postprocess = None):
        """

        :param autofit: if true, scale the scene to fit the whole geometry
        in the viewport.
        """
    
        # First initialize the openGL context
        glutInit(sys.argv)
        glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB | GLUT_DEPTH)
        glutInitWindowSize(width, height)
        glutCreateWindow(bytes(name, encoding="utf-8"))
#        glutHideWindow()
        glutIconifyWindow()
        self.load_model(filename, postprocess = postprocess)


#        glClearColor(0.1,0.1,0.1,1.)
        glShadeModel(GL_SMOOTH)

        glEnable(GL_LIGHTING)

        glEnable(GL_CULL_FACE)
        glEnable(GL_DEPTH_TEST)

        glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)
        glEnable(GL_NORMALIZE)
        glEnable(GL_LIGHT0)

        glutDisplayFunc(self.display)


        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(35.0, width/float(height) , 0.10, 100.0)
        glMatrixMode(GL_MODELVIEW)
        self.set_default_camera()

        if autofit:
            # scale the whole asset to fit into our view frustumÂ·
            self.fit_scene()

        glPushMatrix()

#        glutKeyboardFunc(self.onkeypress)
        glutIgnoreKeyRepeat(1)

        glutMainLoop()


def killApp():
    curses.nocbreak()
    curseScreen.keypad(False)
    curses.echo()
    curses.endwin()


def initCurseScreen():
    global curseScreen
    curseScreen = curses.initscr()
    curses.noecho()
    curses.cbreak()
    curseScreen.keypad(True)
    global curseScreenHeight, curseScreenWidth
    curseScreenHeight, curseScreenWidth = curseScreen.getmaxyx()
    curseScreenHeight -= 1
    curseScreenWidth -= 1


def displayImage(inputFile):
    img = Image.open(args.inputFile).convert("LA")
    global width, height
    width, height = img.size
    data = list(img.getdata())
    pixels = [data[i * width: (i + 1) * width] for i in range(height)]
    pixels.reverse()
    displayData(pixels)


def checkImageInput():
    c = curseScreen.getch()
    if c == -1:
        return
    if c == ord('k'):
        killApp()
        sys.exit(0)


def displayData(data):
        charMap = asciiTools.getCharMap(data, curseScreenWidth, curseScreenHeight)
        curseScreen.clear()
        for r in range(curseScreenHeight):
            curseScreen.addstr(r, 0, charMap[-r])
        curseScreen.refresh()
    
    
if __name__ == '__main__':
    if not len(sys.argv) > 1:
        print("Usage: " + __file__ + " <model>")
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Display with ASCII")
    parser.add_argument("inputFile")
    parser.add_argument("--model", action="store_true")
    parser.add_argument("-x", type=int, default=250)
    parser.add_argument("-y", type=int, default=250)
    args = parser.parse_args()

    global height, width
    height = args.x
    width = args.y

    initCurseScreen()
    if args.model:
        curseScreen.nodelay(1)
        glrender = GLRenderer()
        glrender.render(args.inputFile, fullscreen = False, postprocess = aiProcessPreset_TargetRealtime_MaxQuality)
    else:
        displayImage(args.inputFile)
        while True:
            checkImageInput()
