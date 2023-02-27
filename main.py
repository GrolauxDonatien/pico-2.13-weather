from machine import Pin, SPI
import framebuf
import utime
import time
import network
import usocket as socket
import json
import urequests

########################## Configuration here
ssidRouter     = '***********' #Enter the router name
passwordRouter = '***********' #Enter the router password
API_KEY = '***********' #create at openweathermap web site, then wait a couple hours for the key to become active
LATITUDE = '***********' #grab from https://www.latlong.net
LONGITUDE = '***********'
UNITS = 'metric' # or imperial
########################## End configuration

WEATHER = 'http://api.openweathermap.org/data/2.5/weather?' + 'lat=' + LATITUDE + '&lon=' + LONGITUDE + '&units=' + UNITS +'&appid=' + API_KEY

lut_full_update= [
    0x80,0x60,0x40,0x00,0x00,0x00,0x00,             #LUT0: BB:     VS 0 ~7
    0x10,0x60,0x20,0x00,0x00,0x00,0x00,             #LUT1: BW:     VS 0 ~7
    0x80,0x60,0x40,0x00,0x00,0x00,0x00,             #LUT2: WB:     VS 0 ~7
    0x10,0x60,0x20,0x00,0x00,0x00,0x00,             #LUT3: WW:     VS 0 ~7
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,             #LUT4: VCOM:   VS 0 ~7

    0x03,0x03,0x00,0x00,0x02,                       # TP0 A~D RP0
    0x09,0x09,0x00,0x00,0x02,                       # TP1 A~D RP1
    0x03,0x03,0x00,0x00,0x02,                       # TP2 A~D RP2
    0x00,0x00,0x00,0x00,0x00,                       # TP3 A~D RP3
    0x00,0x00,0x00,0x00,0x00,                       # TP4 A~D RP4
    0x00,0x00,0x00,0x00,0x00,                       # TP5 A~D RP5
    0x00,0x00,0x00,0x00,0x00,                       # TP6 A~D RP6

    0x15,0x41,0xA8,0x32,0x30,0x0A,
]

lut_partial_update = [ #20 bytes
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,             #LUT0: BB:     VS 0 ~7
    0x80,0x00,0x00,0x00,0x00,0x00,0x00,             #LUT1: BW:     VS 0 ~7
    0x40,0x00,0x00,0x00,0x00,0x00,0x00,             #LUT2: WB:     VS 0 ~7
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,             #LUT3: WW:     VS 0 ~7
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,             #LUT4: VCOM:   VS 0 ~7

    0x0A,0x00,0x00,0x00,0x00,                       # TP0 A~D RP0
    0x00,0x00,0x00,0x00,0x00,                       # TP1 A~D RP1
    0x00,0x00,0x00,0x00,0x00,                       # TP2 A~D RP2
    0x00,0x00,0x00,0x00,0x00,                       # TP3 A~D RP3
    0x00,0x00,0x00,0x00,0x00,                       # TP4 A~D RP4
    0x00,0x00,0x00,0x00,0x00,                       # TP5 A~D RP5
    0x00,0x00,0x00,0x00,0x00,                       # TP6 A~D RP6

    0x15,0x41,0xA8,0x32,0x30,0x0A,
]


# In portrait mode, FrameBuffer has two horizontal modes HLSB & HMSB, with different bits direction
# In landscape mode, FrameBuffer has only one mode, which is the wrong one for the ePaper 2.13
# the reverse function reverses the bits direction, using a lookup table (simple & fast)
lookup = [
    0x0, 0x8, 0x4, 0xc, 0x2, 0xa, 0x6, 0xe, 0x1, 0x9, 0x5, 0xd, 0x3, 0xb, 0x7, 0xf
]

def reverse(n):
    return (lookup[n&0b1111]<< 4) | (lookup[n>>4])

EPD_WIDTH = 250
EPD_HEIGHT = 128 # height is really 122 pixels, but the code needs it to be divisible by 8

RST_PIN         = 12
DC_PIN          = 8
CS_PIN          = 9
BUSY_PIN        = 13

FULL_UPDATE = 0
PART_UPDATE = 1

class EPD_2in13(framebuf.FrameBuffer):
    def __init__(self):
        self.reset_pin = Pin(RST_PIN, Pin.OUT)
        
        self.busy_pin = Pin(BUSY_PIN, Pin.IN, Pin.PULL_UP)
        self.cs_pin = Pin(CS_PIN, Pin.OUT)
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT
        
        self.full_lut = lut_full_update
        self.partial_lut = lut_partial_update
        
        self.full_update = FULL_UPDATE
        self.part_update = PART_UPDATE
        
        self.spi = SPI(1)
        self.spi.init(baudrate=4000_000)
        self.dc_pin = Pin(DC_PIN, Pin.OUT)
        
        
        self.buffer = bytearray(self.height * self.width // 8)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.init(FULL_UPDATE)

    def digital_write(self, pin, value):
        pin.value(value)

    def digital_read(self, pin):
        return pin.value()

    def delay_ms(self, delaytime):
        utime.sleep(delaytime / 1000.0)

    def spi_writebyte(self, data):
        self.spi.write(bytearray(data))

    def module_exit(self):
        self.digital_write(self.reset_pin, 0)

    # Hardware reset
    def reset(self):
        self.digital_write(self.reset_pin, 1)
        self.delay_ms(50)
        self.digital_write(self.reset_pin, 0)
        self.delay_ms(2)
        self.digital_write(self.reset_pin, 1)
        self.delay_ms(50)   


    def send_command(self, command):
        self.digital_write(self.dc_pin, 0)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte([command])
        self.digital_write(self.cs_pin, 1)

    def send_data(self, data):
        self.digital_write(self.dc_pin, 1)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte([data])
        self.digital_write(self.cs_pin, 1)
        
    def ReadBusy(self):
        print('busy')
        while(self.digital_read(self.busy_pin) == 1):      # 0: idle, 1: busy
            self.delay_ms(10)    
        print('busy release')
        
    def TurnOnDisplay(self):
        self.send_command(0x22)
        self.send_data(0xC7)
        self.send_command(0x20)        
        self.ReadBusy()

    def TurnOnDisplayPart(self):
        self.send_command(0x22)
        self.send_data(0x0c)
        self.send_command(0x20)        
        self.ReadBusy()

    def init(self, update):
        print('init')
        self.reset()
        if(update == self.full_update):
            self.ReadBusy()
            self.send_command(0x12) # soft reset
            self.ReadBusy()

            self.send_command(0x74) #set analog block control
            self.send_data(0x54)
            self.send_command(0x7E) #set digital block control
            self.send_data(0x3B)

            self.send_command(0x01) #Driver output control
            self.send_data(0x27)
            self.send_data(0x01)
            self.send_data(0x01)
            
            self.send_command(0x11) #data entry mode
            self.send_data(0x01)

            self.send_command(0x44) #set Ram-X address start/end position
            self.send_data(0x00)
            self.send_data(0x0F)    #0x0C-->(15+1)*8=128

            self.send_command(0x45) #set Ram-Y address start/end position
            self.send_data(0x27)   #0xF9-->(249+1)=250
            self.send_data(0x01)
            self.send_data(0x2e)
            self.send_data(0x00)
            
            self.send_command(0x3C) #BorderWavefrom
            self.send_data(0x03)

            self.send_command(0x2C)     #VCOM Voltage
            self.send_data(0x55)    #

            self.send_command(0x03)
            self.send_data(self.full_lut[70])

            self.send_command(0x04) #
            self.send_data(self.full_lut[71])
            self.send_data(self.full_lut[72])
            self.send_data(self.full_lut[73])

            self.send_command(0x3A)     #Dummy Line
            self.send_data(self.full_lut[74])
            self.send_command(0x3B)     #Gate time
            self.send_data(self.full_lut[75])

            self.send_command(0x32)
            for count in range(70):
                self.send_data(self.full_lut[count])

            self.send_command(0x4E)   # set RAM x address count to 0
            self.send_data(0x00)
            self.send_command(0x4F)   # set RAM y address count to 0X127
            self.send_data(0x0)
            self.send_data(0x00)
            self.ReadBusy()
        else:
            self.send_command(0x2C)     #VCOM Voltage
            self.send_data(0x26)

            self.ReadBusy()

            self.send_command(0x32)
            for count in range(70):
                self.send_data(self.partial_lut[count])

            self.send_command(0x37)
            self.send_data(0x00)
            self.send_data(0x00)
            self.send_data(0x00)
            self.send_data(0x00)
            self.send_data(0x40)
            self.send_data(0x00)
            self.send_data(0x00)

            self.send_command(0x22)
            self.send_data(0xC0)
            self.send_command(0x20)
            self.ReadBusy()

            self.send_command(0x3C) #BorderWavefrom
            self.send_data(0x01)
        return 0       

      
    def display(self, image):
        self.send_command(0x24)
        h = int(self.height/8)
        for j in range(0, self.width):
            for i in range(0, h):
                self.send_data(reverse(image[i*self.width + (self.width-j-1)]))   
        self.TurnOnDisplay()
        
    def displayPartial(self, image):
        self.send_command(0x24)
        h = int(self.height/8)
        for j in range(0, self.width):
            for i in range(0, h):
                self.send_data(reverse(image[i*self.width + (self.width-j-1)]))   
                
        self.send_command(0x26)
        for j in range(0, self.width):
            for i in range(0, h):
                self.send_data(~reverse(image[i*self.width + (self.width-j-1)]))   
        self.TurnOnDisplayPart()

    def displayPartBaseImage(self, image):
        self.send_command(0x24)
        h = int(self.height/8)
        for j in range(0, self.width):
            for i in range(0, h):
                self.send_data(reverse(image[i*self.width + (self.width-j-1)]))   
                
        self.send_command(0x26)
        for j in range(0, self.width):
            for i in range(0, h):
                self.send_data(reverse(image[i*self.width + (self.width-j-1)]))   
        self.TurnOnDisplay()
    
    def Clear(self, color):
        self.send_command(0x24)
        h = int(self.height/8)
        for j in range(0, self.width):
            for i in range(0, h):
                self.send_data(color)   
        self.send_command(0x26)
        for j in range(0, self.width):
            for i in range(0, h):
                self.send_data(color)   
                                
        self.TurnOnDisplay()

    def sleep(self):
        self.send_command(0x10) #enter deep sleep
        self.send_data(0x03)
        self.delay_ms(2000)
        self.module_exit()
        
        
# now onto the code itself

def STA_Setup(ssidRouter,passwordRouter, sta_if):
    if not sta_if.isconnected():
        print('connecting to',ssidRouter)
        sta_if.active(True)
        sta_if.connect(ssidRouter,passwordRouter)
        attempt = 0
        while attempt < 60 and not sta_if.isconnected():
            attempt += 1
            utime.sleep(1000.0)
        if sta_if.isconnected():
            print('Connected, IP address:', sta_if.ifconfig())
        else:
            print('Could not connect')
    return sta_if


def init(epd):
    epd.Clear(0xff)
    epd.fill(0xff)
    epd.fill_rect(48, 0, 2, 122, 0x00)
    epd.display(epd.buffer)
    epd.init(epd.part_update)



def on2(s):
    s = str(s)
    if len(s)==0:
        return "00"
    elif len(s)==1:
        return "0"+s
    else:
        return s
    
def loop(sta_if, epd):
    lastm = ""
    lasth = ""
    while True:
        t = time.localtime()
        h = str(t[0])+':'+ str(t[1])+':'+str(t[2])+':'+str(t[3])
        m = h+':'+str(t[4])
        if m != lastm:
            lastm = m
            epd.fill_rect(0, 0, 47, 10, 0xff)
            epd.text(on2(t[3])+":"+on2(t[4]), 0, 0, 0x00)
            epd.displayPartial(epd.buffer)
        if h != lasth:
            if not sta_if.isconnected():
                STA_Setup(ssidRouter,passwordRouter, sta_if)
            if not sta_if.isconnected():
                continue                
            lasth = h
            epd.fill_rect(50, 0, 200, 122, 0xff)
            try:
                resp = urequests.get(WEATHER).json()
                epd.text(resp["weather"][0]["description"], 52, 0, 0x00)
                epd.fill_rect(52, 13, 200, 1, 0x00)            
                epd.text("Temp:  "+str(resp["main"]["temp"])+"c", 52, 19, 0x00)
                epd.text("Feels: "+str(resp["main"]["feels_like"])+"c", 52, 34, 0x00)
                epd.text("Min:   "+str(resp["main"]["temp_min"])+"c", 52, 49, 0x00)
                epd.text("Max:   "+str(resp["main"]["temp_max"])+"c", 52, 64, 0x00)
                epd.text("Pressure: "+str(resp["main"]["pressure"])+"hPa", 52, 94, 0x00)
                epd.text("Humidity: "+str(resp["main"]["humidity"])+"%", 52, 109, 0x00)
            except:
                # give up
                pass
            epd.displayPartial(epd.buffer)
        epd.delay_ms(1000)


if __name__=='__main__':
    sta_if = network.WLAN(network.STA_IF)
    epd = EPD_2in13()
    init(epd)
    loop(sta_if, epd)
