import pyglet
from pyglet.gl import *
from pyglet.window import key
from chunk import Chunk
import cPickle as pickle
import blocks
from util import sign
import player
from math import sin, cos, radians, sqrt
import os

class Game:
    def __init__(self,world,generator,offsets):
        self.window = pyglet.window.Window(fullscreen=True)
        self.window.push_handlers(self)

        self.chunks = {}
        self.player = player.Player(0,0,0,blocks.Stone)

        self.window.set_exclusive_mouse(True)

        self.keys = key.KeyStateHandler()
        self.window.push_handlers(self.keys)

        pyglet.clock.schedule(self.update)

        glClearColor(0.3,0.5,1.0,1.0)

        self.off_number = 0
        self.close_number = 0

        self.key_listing = self.chunks.keys()

        self.world = world

        self.fps_display = pyglet.clock.ClockDisplay()

        self.inventory = False
        self.invent_pos = (0,0)

        self.generator = generator
        self.generator.blocks = blocks
        self.offsets = offsets

    def update(self,dt):
        self.motion_amount = dt * 5
        w=self.keys[key.W];a=self.keys[key.A];s=self.keys[key.S];d=self.keys[key.D]

        if self.keys[key.R]:
            self.player.y += self.motion_amount
        elif self.keys[key.F]:
            self.player.y -= self.motion_amount
        #old_position = self.player.x,self.player.y,self.player.z
        
        if w&a:
            self.player.apply_motion(self,self.motion_amount,45)
        elif w&d:
            self.player.apply_motion(self,self.motion_amount,-45)
        elif s&d:
            self.player.apply_motion(self,self.motion_amount,-135)
        elif s&a:
            self.player.apply_motion(self,self.motion_amount,135)
        elif w:
            self.player.apply_motion(self,self.motion_amount)
        elif s:
            self.player.apply_motion(self,self.motion_amount,180)
        elif a:
            self.player.apply_motion(self,self.motion_amount,90)
        elif d:
            self.player.apply_motion(self,self.motion_amount,-90)

        player_chunk = (int(self.player.x//8),int(self.player.y//8),int(self.player.z//8))

        if self.offsets.do_wide:
            self.off_number += 1
            self.off_number %= len(self.offsets.wide)
            off = self.offsets.wide[self.off_number]
            self.check_and_load(player_chunk[0]+off[0],player_chunk[1]+off[1],player_chunk[2]+off[2])

        self.close_number += 1
        self.close_number %= len(self.offsets.close)
        close = self.offsets.close[self.close_number]
        self.check_and_load(player_chunk[0]+close[0],player_chunk[1]+close[1],player_chunk[2]+close[2])

        if not self.key_listing:
            self.key_listing = self.chunks.keys()


        to_check = self.key_listing.pop()

        dx = to_check[0] - player_chunk[0]
        dy = to_check[1] - player_chunk[1]
        dz = to_check[2] - player_chunk[2]

        if sqrt(dx*dx+dy*dy+dz*dz) > self.offsets.deletion_range:
            self.unload(*to_check)

    def unload(self,cx,cy,cz):
        data = []
        chunk = self.chunks[(cx,cy,cz)]
        for block in chunk.grid:
            if block:
                data.append((block.name,block.save_data()))
            else:
                data.append(None)
        f=open('worlds/'+self.world+'/'+str(cx)+' '+str(cy)+' '+str(cz),'wb')

        pickle.dump(data,f,-1)
        f.close()
        del self.chunks[(cx,cy,cz)]

    def check_and_load(self,cx,cy,cz):
        player_chunk = (cx,cy,cz)
        if player_chunk not in self.chunks:
            chunk_listing = os.listdir('worlds/'+self.world)
            if (str(cx)+' '+str(cy)+' '+str(cz)) in chunk_listing:
                data = []
                f = open('worlds/'+self.world+'/'+str(cx)+' '+str(cy)+' '+str(cz),'rb')
                d = pickle.load(f)
                f.close()
                for item in d:
                    if item is None:
                        data.append(None)
                    else:
                        data.append(blocks.names[item[0]](*item[1]))
                gen_features=False
            else:
                gen_features = True
                data = self.generator.generate(cx,cy,cz)
                
            #print data
            self.chunks[player_chunk] = Chunk(player_chunk,data)
            if gen_features:
                self.generator.features(cx,cy,cz,self)
                pass
            
    def set_3d(self):
        width,height = self.window.width,self.window.height
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(65, width / float(height), .1, 1000)
        glMatrixMode(GL_MODELVIEW)

    def set_2d(self):
        width,height = self.window.width,self.window.height
        glViewport(0, 0, width, height)
        glMatrixMode(gl.GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, width, 0, height, -1, 1)
        glMatrixMode(gl.GL_MODELVIEW)

    def set_block(self,x,y,z,block):
        chunk = (x//8,y//8,z//8)
        inner = (x%8, y%8, z%8 )

        if chunk not in self.chunks:
            self.check_and_load(*chunk)

        self.chunks[chunk].set_block(*inner,block=block)

    def get_block(self,x,y,z):
        chunk = (x//8,y//8,z//8)
        inner = (x%8, y%8, z%8 )

        if chunk not in self.chunks:
            return None
        else:
            return self.chunks[chunk].get_block(*inner)
        
    def on_draw(self):
        glLineWidth(2.0)
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        glBlendEquation(GL_FUNC_ADD)
        glEnable(GL_DEPTH_TEST)
        self.set_3d()
        self.player.transform()
        glEnable(GL_FOG)
        glFogi(GL_FOG_MODE, GL_LINEAR)
        glFogf(GL_FOG_START, 2.0) #2
        glFogf(GL_FOG_END, 40.0)
        glFogfv(GL_FOG_COLOR,(GLfloat*3)(0.3,0.5,1.0))
        
        for chunk in self.chunks.itervalues():
            chunk.draw()
        b = self.cast_ray()
        if b:
            
##            #print b.x,b.y,b.z
            glColor4f(0,0,0,1.0)

            glBegin(GL_LINE_STRIP)
            v = b.get_selectbox_vertices()
            for index in xrange(0,len(v),3):
                glVertex3f(v[index],v[index+1],v[index+2])
            glEnd()
##            glVertex3f(b.x-scale,b.y+0.6,b.z-scale)
##            glVertex3f(b.x+scale,b.y+0.6,b.z-scale)
##            glVertex3f(b.x+scale,b.y+0.6,b.z+scale)
##            glVertex3f(b.x-scale,b.y+0.6,b.z+scale)
##            glEnd()
        glDisable(GL_FOG)
        self.set_2d()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        if self.inventory:
            start_pos = [self.window.width//2-len(blocks.blocks)*32,self.window.height//2]
            glBegin(GL_QUADS)
            for block in blocks.blocks:
                glColor3f(*block.invent_color)
                glVertex2f(start_pos[0]-32,start_pos[1]-32)
                glVertex2f(start_pos[0]+32,start_pos[1]-32)
                glVertex2f(start_pos[0]+32,start_pos[1]+32)
                glVertex2f(start_pos[0]-32,start_pos[1]+32)
                start_pos[0] += 64
            glEnd()
                
            
        glColor4f(1,1,1,0.5)
        if not self.inventory:
            cx,cy = self.window.width//2,self.window.height//2
        else:
            cx,cy = self.invent_pos
        glBegin(GL_LINES)
        glVertex2f(cx-10,cy)
        glVertex2f(cx+10,cy)
        glVertex2f(cx,cy-10)
        glVertex2f(cx,cy+10)
        glEnd()
        self.fps_display.draw()

    def as_ints(self,x,y,z):
        return int(round(x)),int(round(y)),int(round(z))

    def cast_ray(self):
        vx = -sin(radians(self.player.angle_y)) * cos(radians(self.player.angle_x)) / 100.0
        vy = sin(radians(self.player.angle_x)) / 100.0
        vz = -cos(radians(self.player.angle_y)) * cos(radians(self.player.angle_x)) / 100.0
        #print vx,vy,vz
        px,py,pz = self.player.x,self.player.y,self.player.z

        for _ in xrange(1500):
            r= self.get_block(*self.as_ints(px,py,pz))
            if r:
                return r
            px += vx
            py += vy
            pz += vz
        return None

    def cast_to_side(self):
        vx = -sin(radians(self.player.angle_y)) * cos(radians(self.player.angle_x)) / 100.0
        vy = sin(radians(self.player.angle_x)) / 100.0
        vz = -cos(radians(self.player.angle_y)) * cos(radians(self.player.angle_x)) / 100.0
        #print vx,vy,vz
        px,py,pz = self.player.x,self.player.y,self.player.z

        for _ in xrange(1500):
            r= self.get_block(*self.as_ints(px,py,pz))
            if r:
                dx,dy,dz = (px-r.x,py-r.y,pz-r.z)
                if abs(dx) > max(abs(dy),abs(dz)):
                    return r.x+sign(dx),r.y,r.z
                elif abs(dy) > max(abs(dx),abs(dz)):
                    return r.x,r.y+sign(dy),r.z
                else:
                    return r.x,r.y,r.z+sign(dz)
                
            px += vx
            py += vy
            pz += vz
        return None
        
    def on_mouse_motion(self,x,y,dx,dy):
        if not self.inventory:
            self.player.angle_y -= dx *0.75 #NOTE: These are reserved.
            self.player.angle_x += dy *0.75
            self.player.angle_x = max(min(self.player.angle_x, 90),-90)
        else:
            self.invent_pos = (self.invent_pos[0]+dx,self.invent_pos[1]+dy)
            
    def on_mouse_press(self,x,y,button,modifiers):
        if button == pyglet.window.mouse.LEFT:
            if self.inventory:
                x,y = self.invent_pos
                self.inventory = False
                x -= (self.window.width//2 - len(blocks.blocks)*32) - 32
                y -= self.window.height//2
                #print x,y
                if abs(y) > 32:
                    return
                elif x >= (len(blocks.blocks)*64):
                    return
                else:
                    self.player.current_block = blocks.blocks[x//64]
            else:
                b = self.cast_ray()
                if b is not None:
                    
                    self.set_block(b.x,b.y,b.z,None)
        elif button == pyglet.window.mouse.RIGHT:
            b = self.cast_to_side()
            if b is not None:
                self.set_block(b[0],b[1],b[2],self.player.current_block(b[0],b[1],b[2]))

    def on_key_press(self,key,modifiers):
        if key == pyglet.window.key.E:
            self.inventory = not self.inventory
            self.invent_pos = (self.window.width//2,self.window.height//2)
        if key == pyglet.window.key.ESCAPE:
            for chunk in self.chunks.keys():
                self.unload(*chunk)
            raise SystemExit
