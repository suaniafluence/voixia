from twisted.internet import reactor, protocol

class SIPProtocol(protocol.DatagramProtocol):
    def datagramReceived(self, data, addr):
        message = data.decode('utf-8')
        print(f"Received SIP message from {addr}: {message}")
        if "INVITE" in message or "REGISTER" in message:
            response = (
                "SIP/2.0 200 OK\r\n"
                "Via: SIP/2.0/UDP localhost:5060;branch=z9hG4bK-1\r\n"
                "From: <sip:user@localhost>\r\n"
                "To: <sip:user@localhost>;tag=1\r\n"
                "Call-ID: 1\r\n"
                "CSeq: 1 REGISTER\r\n"
                "Content-Length: 0\r\n\r\n"
            )
            self.transport.write(response.encode('utf-8'), addr)

def start_sip_server():
    reactor.listenUDP(5060, SIPProtocol())
    print("SIP server running on port 5060")