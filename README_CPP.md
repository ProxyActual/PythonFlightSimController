# C++ UDP Client for MSFS

## Compilation

```bash
make
```

Or compile manually:
```bash
g++ -std=c++11 -o udp_client udp_client.cpp
```

## Usage

Run the server first:
```bash
python SimConnection.py
```

Then run the client:
```bash
./udp_client
```

## Simple Function

The core function is super simple:

```cpp
double airspeed = get_msfs_value("AIRSPEED_INDICATED");
```

You can also specify server IP and port:
```cpp
double altitude = get_msfs_value("PLANE_ALTITUDE", "192.168.1.100", 5005);
```

Returns -1.0 on error.
