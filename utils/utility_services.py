import socket


class UtilityServices:

    def get_ip_address(self, request) -> str:
        """
        Get Client's Current IP Address
        """
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)

        return ip_address
