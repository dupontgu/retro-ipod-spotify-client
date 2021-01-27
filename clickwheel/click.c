// To compile on the pi (after installing pigpio):
// gcc -Wall -pthread -o click click.c -lpigpio -lrt

#include <pigpio.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h> 
#include <string.h> 
#include <sys/types.h> 
#include <sys/socket.h> 
#include <arpa/inet.h> 
#include <netinet/in.h> 

#define CLOCK_PIN 23
#define DATA_PIN 25
#define HAPTIC_PIN 26
#define BIT_COUNT 32
#define PORT 9090 
#define MAXLINE 1024 

#define CENTER_BUTTON_BIT 7
#define LEFT_BUTTON_BIT 9
#define RIGHT_BUTTON_BIT 8
#define UP_BUTTON_BIT 11
#define DOWN_BUTTON_BIT 10
#define WHEEL_TOUCH_BIT 29

#define BUFFER_SIZE 3
#define BUTTON_INDEX 0
#define BUTTON_STATE_INDEX 1
#define WHEEL_POSITION_INDEX 2

// used to store the current packet
uint32_t bits = 0;
// used to store the previous full packet
uint32_t lastBits = 0;
uint8_t bitIndex = 0;
uint8_t oneCount = 0;
uint8_t recording = 0;
// indicates whether the data pin is high or low
uint8_t dataBit = 1;
uint8_t lastPosition = 255;
int hapticWaveId = -1;

char buttons[] = { 
    CENTER_BUTTON_BIT, 
    LEFT_BUTTON_BIT, 
    RIGHT_BUTTON_BIT, 
    UP_BUTTON_BIT, 
    DOWN_BUTTON_BIT, 
    WHEEL_TOUCH_BIT
};

// all valid click wheel packets start with this
const uint32_t PACKET_START = 0b01101;

int sockfd; 
char buffer[BUFFER_SIZE]; 
char prev_buffer[BUFFER_SIZE];
struct sockaddr_in servaddr; 

// helper function to print packets as binary
void printBinary(uint32_t value) {
    for(uint8_t i = 0; i < 32; i++) {
        if (value & 1)
            printf("1");
        else
            printf("0");

        value >>= 1;
    }
    printf("\n");
}

// parse packet and broadcast data
void sendPacket() {
    if ((bits & PACKET_START) != PACKET_START) {
        return;
    }
    for (size_t i = 0; i < BUFFER_SIZE; i++) {
        buffer[i] = -1;
    }
    
    for (size_t i = 0; i < sizeof(buttons); i++) {
        char buttonIndex = buttons[i];
        if ((bits >> buttonIndex) & 1 && !((lastBits >> buttonIndex) & 1)) {
            buffer[BUTTON_INDEX] = buttonIndex;
            buffer[BUTTON_STATE_INDEX] = 1;
            printf("button pressed: %d\n", buttonIndex);
        } else if (!((bits >> buttonIndex) & 1) && (lastBits >> buttonIndex) & 1) {
            buffer[BUTTON_INDEX] = buttonIndex;
            buffer[BUTTON_STATE_INDEX] = 0;
            printf("button released: %d\n", buttonIndex);
        }
    }
    uint8_t wheelPosition = (bits >> 16) & 0xFF;
    // send haptics every other position. too sensitive otherwise
    if (wheelPosition != lastPosition && wheelPosition % 2 == 0) {
        if (hapticWaveId != -1) {
            gpioWaveTxSend(hapticWaveId, PI_WAVE_MODE_ONE_SHOT);
        }
        lastPosition = wheelPosition;
    }
    buffer[WHEEL_POSITION_INDEX] = wheelPosition;
    if (memcmp(prev_buffer, buffer, BUFFER_SIZE) == 0) {
        return;
    }
    printf("position %d\n", wheelPosition);
    lastBits = bits;
    sendto(sockfd, (const char *)buffer, BUFFER_SIZE, 
        MSG_CONFIRM, (const struct sockaddr *) &servaddr,  
            sizeof(servaddr)); 
    memcpy(prev_buffer, buffer, BUFFER_SIZE);
}

// Function to set the kth bit of n 
int setBit(int n, int k) { 
    return (n | (1 << (k - 1))); 
} 
  
// Function to clear the kth bit of n 
int clearBit(int n, int k) { 
    return (n & (~(1 << (k - 1)))); 
} 

void onClockEdge(int gpio, int level, uint32_t tick) {
    if (!level) {
        // only care about rising edge
        return;
    }
    if (dataBit == 0) {
        recording = 1;
        oneCount = 0;
    } else {
        // 32 1's in a row means we're definitely not in the middle of a packet
        if (++oneCount >= BIT_COUNT) {
            recording = 0;
            bitIndex = 0;
        }
    }
    // in the middle of the packet
    if (recording == 1) {
        if (dataBit) {
            bits = setBit(bits, bitIndex);
        } else {
            bits = clearBit(bits, bitIndex);
        }
        // we've collected the whole packet
        if (++bitIndex == 32) {
            bitIndex = 0;
            sendPacket();
        }
    }
}

void onDataEdge(int gpio, int level, uint32_t tick) {
    dataBit = level;
}

int main(void *args){
  
    // Creating socket file descriptor 
    if ( (sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0 ) { 
        perror("socket creation failed"); 
        exit(EXIT_FAILURE); 
    } 
  
    memset(&servaddr, 0, sizeof(servaddr)); 
      
    servaddr.sin_family = AF_INET; 
    servaddr.sin_port = htons(PORT); 
    servaddr.sin_addr.s_addr = INADDR_ANY; 

    if (gpioInitialise() < 0) {
       exit(1);
    }

    // haptic waveform - just a simple on-off pulse
    gpioSetMode(HAPTIC_PIN, PI_OUTPUT);
    gpioPulse_t pulse[2];
    pulse[0].gpioOn = (1<<HAPTIC_PIN);
    pulse[0].gpioOff = 0;
    pulse[0].usDelay = 8000;

    pulse[1].gpioOn = 0;
    pulse[1].gpioOff = (1<<HAPTIC_PIN);
    pulse[1].usDelay = 2000;

    gpioWaveAddNew();

    gpioWaveAddGeneric(2, pulse);

    hapticWaveId = gpioWaveCreate();
    gpioSetPullUpDown(CLOCK_PIN, PI_PUD_UP);
    gpioSetPullUpDown(DATA_PIN, PI_PUD_UP);
    gpioSetAlertFunc(CLOCK_PIN, onClockEdge);
    gpioSetAlertFunc(DATA_PIN, onDataEdge);

    while(1) {

    };
    gpioTerminate();
}