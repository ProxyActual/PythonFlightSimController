#include <iostream>
#include <string>
#include <cstring>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>

/**
 * Simple function to request a value from the MSFS UDP server
 * 
 * @param sim_var_name The SimConnect variable name to request (e.g., "AIRSPEED_INDICATED")
 * @param server_ip The IP address of the UDP server (default: "127.0.0.1")
 * @param server_port The port of the UDP server (default: 5005)
 * @return The value as a double, or -1.0 on error
 */
double get_msfs_value(const std::string& sim_var_name, 
                      const std::string& server_ip = "127.0.0.1", 
                      int server_port = 5005) {
    int sock;
    struct sockaddr_in server_addr;
    char buffer[1024];
    
    // Create UDP socket
    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        std::cerr << "Error creating socket" << std::endl;
        return -1.0;
    }
    
    // Set timeout (1 second)
    struct timeval tv;
    tv.tv_sec = 1;
    tv.tv_usec = 0;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    
    // Setup server address
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(server_port);
    server_addr.sin_addr.s_addr = inet_addr(server_ip.c_str());
    
    // Send request
    ssize_t sent = sendto(sock, sim_var_name.c_str(), sim_var_name.length(), 0,
                          (struct sockaddr*)&server_addr, sizeof(server_addr));
    if (sent < 0) {
        std::cerr << "Error sending request" << std::endl;
        close(sock);
        return -1.0;
    }
    
    // Receive response
    socklen_t addr_len = sizeof(server_addr);
    ssize_t received = recvfrom(sock, buffer, sizeof(buffer) - 1, 0,
                                (struct sockaddr*)&server_addr, &addr_len);
    
    close(sock);
    
    if (received < 0) {
        std::cerr << "Error receiving response (timeout or connection issue)" << std::endl;
        return -1.0;
    }
    
    buffer[received] = '\0';
    
    try {
        return std::stod(buffer);
    } catch (...) {
        std::cerr << "Error parsing response: " << buffer << std::endl;
        return -1.0;
    }
}


// Example usage
int main() {
    std::cout << "MSFS UDP Client (C++)" << std::endl;
    std::cout << "=====================" << std::endl;
    
    // Request AIRSPEED_INDICATED from the server
    for (int i = 0; i < 10; i++) {
        double airspeed = get_msfs_value("AIRSPEED_INDICATED");

        if(i > 5)
        {
            get_msfs_value("G_FORCE");
        }
        
        if (airspeed >= 0) {
            std::cout << "Airspeed: " << airspeed << " knots" << std::endl;
        } else {
            std::cout << "Failed to get airspeed" << std::endl;
        }
        
        sleep(1);
    }
    
    return 0;
}
