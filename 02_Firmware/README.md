
## Configuring your Arduino IDE to compile a new firmware for your Wind Turbines

If you never used Arduino Before, please visit [this link](https://www.arduino.cc/en/Guide) to download the IDE and learn about how this platform. Inside this directory you will find an Arduino Project. Follow the instructions bellow to configure your environment and then use this project to create a firmware for your Wind Turbines.

### Preparing a package for the Arduino/MPU6050 library
We need to clone and prepare two .zip files with the libraries: MPU6050 and I2CDev. Run the following Bash code to get the library and create the packages.

```bash
# cloning the libraries repo
git clone https://github.com/jrowberg/i2cdevlib

cd i2cdevlib/Arduino/I2Cdev
zip -r ../../../I2Cdev.zip *
cd ../MPU6050
zip -r ../../../MPU6050.zip *

```

### Installing the required libraries

In your **Arduino IDE**:
  1. Click on **Sketch** --> **Include Library** --> **Manage Libraries...**
  1. Search for **Adafruit BME680**
  1. Select the version **1.1.1** and install
<p align="center">    
    <img src="/imgs/install_adafruit_BME680.png" width="600px"></img>    
</p>

  1. Now, click on **Sketch** --> **Include Library** --> **Add .ZIP Library**
  1. Upload one of the .zip files you created before (I2Cdev.zip or MPU6050.zip)
  1. Repeat this process for the other .zip file

### Modify Adafruit_BME680.cpp
Make sure you installed **Adafruit BME680 version 1.1.1** before executing this step.  
Open the local directory where Aduino installs libraries. If you're using a MacOS/Linux machine, this is the dir:  
**~/Documents/Arduino/libraries/**  

Edit the following file and comment line 129: **Adafruit_BME680_Library/Adafruit_BME680.cpp**  
 
**From**:  
 ```c++
 _wire->begin();
 ```

**To**:
```c++
//_wire->begin();
```

### Select the correct board
In your **Arduino IDE**:
  1. Click on **Tools** --> **Board** --> **Arduino AVR Boards** --> **Arduino Pro or Pro Mini**
  1. Then click on **Tools** --> **Processor** --> **ATmega382P (3.3, 8MHz)**
  2. Connect your board to the computer using an FTDI module;
  3. Then select the correct port by clicking on: **Tools** --> **Port** --> **<<port_used_by_arduino>>**

<p align="center">    
    <img src="/imgs/board_select.png" width="600px"></img>    
</p>


Now your environment is ready to compile the firmware. Load the arduino project from this folder, compile it and upload it to your arduino.


