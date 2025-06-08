sudo systemctl stop wpa_supplicant
echo "stopping wpa" 
sudo rfkill unblock wifi
echo "unblocking wifi"

sudo ip link set wlan0 up
echo "bringing lan0 up"
sudo ifconfig wlan0 192.168.4.1 netmask 255.255.255.0
echo "Assigning static IP"
sudo systemctl restart hostapd
echo "restarting hostapd"
sudo systemctl restart dnsmasq
echo "restarting dnsmasq"

echo "Hotspot should now be live."
