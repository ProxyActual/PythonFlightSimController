CXX = g++
CXXFLAGS = -std=c++11 -Wall -O2

all: udp_client

udp_client: udp_client.cpp
	$(CXX) $(CXXFLAGS) -o udp_client udp_client.cpp

clean:
	rm -f udp_client

.PHONY: all clean
