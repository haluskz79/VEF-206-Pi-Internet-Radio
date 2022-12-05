import RPi.GPIO as GPIO
import os
import os.path
import signal
import colorsys
import ioexpander as io
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from ST7789 import ST7789
from time import sleep

GPIO.setmode(GPIO.BCM)

#Initialization of Pimoroni screen
SPI_SPEED_MHZ = 80
screen = ST7789(
    rotation=180,  # Needed to display the right way up on Pirate Audio
    port=0,       # SPI port
    cs=1,         # SPI port Chip-select channel
    dc=9,         # BCM pin used for data/command
    backlight=13,
    spi_speed_hz=SPI_SPEED_MHZ * 1000 * 1000
)
width = screen.width
height = screen.height

img_off = Image.new('RGB', (width, height), color = (0,0,0))
img_on = Image.new('RGB', (width, height), color = (0,0,0)) 
img_shutdown = Image.new('RGB', (width, height), color = (0,0,0)) 
draw_off = ImageDraw.Draw(img_off)
draw_on = ImageDraw.Draw(img_on)
draw_shutdown = ImageDraw.Draw(img_shutdown)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)

#Initialization of RGB Pimoroni potentiometer (LEDs not used)
I2C_ADDR = 0x0E  # 0x18 for IO Expander, 0x0E for the potentiometer breakout
POT_ENC_A = 12
POT_ENC_B = 3
POT_ENC_C = 11
ioe = io.IOE(i2c_addr=I2C_ADDR)
ioe.set_mode(POT_ENC_A, io.PIN_MODE_PP)
ioe.set_mode(POT_ENC_B, io.PIN_MODE_PP)
ioe.set_mode(POT_ENC_C, io.ADC)
ioe.output(POT_ENC_A, 1)
ioe.output(POT_ENC_B, 0)

#Initialization of KY-040 - rotary encoder for radio station switch and system shutdown
def swClicked():
        #draw "OFF" text for 2 seconds before system is halted
        draw_shutdown.text((15,130), "OFF", font = font, fill=(255,255,255))
        screen.display(img_shutdown)
        sleep(2)
        os.system('sudo shutdown now')

clk = 27
dt = 22
sw = 15
GPIO.setup(clk, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(dt, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(sw, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(sw, GPIO.FALLING, callback=swClicked, bouncetime=300)

#Main code
counter = 0
clkLastState = GPIO.input(clk)

#Loop for checking internet connection for a start, once status is online loop is broken and script continues further
while True:
    swState = GPIO.input(sw)
    response = os.system("ping -c 2 www.google.com > /dev/null ")
    if (response == 0):
        print("online")
        draw_on.text((10,130),"online", font = font, fill = (0,255,0))
        screen.display(img_on) 
	sleep(.5)
	break
    elif (swState == 0): #Option to shutdown system when pushing KY-040 encoder button
        swClicked()
    else:
	print("offline")
        draw_off.text((10,130),"offline", font=font, fill = (255,0,0))
        screen.display(img_off)
        sleep(.5)

#To find out current number of radio stations/icons
station_dir_path = "/home/pi/radio/stations"
pocet_stanic = 0
for path in os.listdir(station_dir_path):
    if os.path.isfile(os.path.join(station_dir_path,path)):
        pocet_stanic += 1
        print("Number of radio stations = " + str(pocet_stanic))

i = 1	
vol = 25
#Reads and applies last radio station and volume level
if (os.path.exists("/home/pi/radio/conf.txt") == True and os.path.getsize("/home/pi/radio/conf.txt")>0):
    conf_file = open("/home/pi/radio/conf.txt", "r")
    conf_str = conf_file.read()
    print(conf_str)
    conf_file.close()
    i= int(conf_str.split(',')[0])
    vol=int(conf_str.split(',')[1])
else:
    i=i
    vol = vol

os.system('amixer -q -D pulse sset Master 30%') #flag -q is for not displaying command output
screen.display(Image.open("/home/pi/radio/icons/%s.jpg" % i))
os.system('cvlc /home/pi/radio/stations/%s.m3u &' % i)

#Station switching, volume control, system shutdown
try:
    while True:
                    screen.display(Image.open("/home/pi/radio/icons/%s.jpg" % i))
                    #Station switching
                    clkState = GPIO.input(clk)
                    dtState = GPIO.input(dt)
                    swState = GPIO.input(sw)
                    if (swState == 0): #Option to shutdown system when pushing KY-040 encoder button
                        swClicked()
                    #    sleep (.2)
                    elif clkState != clkLastState:
                            if dtState != clkState:
                                    counter += 1
                                    i += 1
                                    if i > pocet_stanic:
                                        i = 1
                                    else:
                                        i = i
                                    print ("Station %s" % i)
                                    screen.display(Image.open("/home/pi/radio/icons/%s.jpg" % i))
                                    os.system('cvlc /home/pi/radio/stations/%s.m3u &' % i)
                                    #sleep(.2)
                                    print ("Switched to next station:" + str(i))
                            else:
                                    counter -= 1
                                    i -= 1
                                    if i < 1:
                                        i = pocet_stanic
                                    else:
                                        i = i
                                    print ("Station %s" % i)
                                    screen.display(Image.open("/home/pi/radio/icons/%s.jpg" % i))
                                    os.system('cvlc /home/pi/radio/stations/%s.m3u &' % i)
                                    print ("Switched to previous station:" + str(i))
                            print counter
                            clkLastState = clkState
                            sleep(0.1)
                    else:
                        sleep(.2)
                    #volume change
                    analog = ioe.input(POT_ENC_C)
                    vol = int(abs(analog-3)*30)
                    #print(vol)
                    os.system("amixer -q -D pulse sset Master " + str(vol) + "%") #flag -q is for not displaying command output
                    #Save current station and volume into conf.txt
                    conf_file = open("/home/pi/radio/conf.txt", "w")
                    conf_file.write(str(i)+","+str(vol))
                    conf_file.close()
finally:
        GPIO.cleanup()
