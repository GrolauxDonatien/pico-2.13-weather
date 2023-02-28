# pico-2.13-weather
Raspberry Pico W with waveshare 2.13" epaper weather station in landscape mode

There are many weather station projects, but I could not find one in that uses the 2.13" epaper from waveshare, using SPI interface on the Pico W, *in landscape mode*.
The code uses worldtimeapi.org to set up the time when the Pico boots up. 
Then it uses openweathermap.org to fetch weather data (you'll need an API key for that).

Instructions:
1. Fill in the gaps in the configuration section of main.py.
2. Upload main.py to the Pico.
