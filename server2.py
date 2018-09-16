# coding=utf8
# !/usr/bin/python

import struct, socket, sys
import hashlib
import threading, random
import time
from base64 import b64encode, b64decode

connectionlist = {}


# python3k 版本recv返回字节数组
def decode(data):
    if not len(data):
        return False
    #print(data)
    length = data[1] & 127
    if length == 126:
        mask = data[4:8]
        raw = data[8:]
    elif length == 127:
        mask = data[10:14]
        raw = data[14:]
    else:
        mask = data[2:6]
        raw = data[6:]
    ret = ''
    for cnt, d in enumerate(raw):
        ret += chr(d ^ mask[cnt % 4])
    return ret


def encode(data):
    data = str.encode(data)
    head = b'\x81'

    if len(data) < 126:
        head += struct.pack('B', len(data))
    elif len(data) <= 0xFFFF:
        head += struct.pack('!BH', 126, len(data))
    else:
        head += struct.pack('!BQ', 127, len(data))
    return head + data


def sendMessage(message):
    global connectionlist
    for connection in connectionlist.values():
        connection.send(encode(message))


def deleteconnection(item):
    global connectionlist
    del connectionlist['connection' + item]


class WebSocket(threading.Thread):
    GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self, conn, index, name, remote, path="/"):
        threading.Thread.__init__(self)
        self.conn = conn
        self.index = index
        self.name = name
        self.remote = remote
        self.path = path
        self.buffer = ""

    def run(self):
        print('Socket%s Start!' % self.index)
        headers = {}
        self.handshaken = False

        while True:
            if self.handshaken == False:
                print('Socket%s Start Handshaken with %s!' % (self.index, self.remote))
                self.buffer += bytes.decode(self.conn.recv(1024))

                if self.buffer.find('\r\n\r\n') != -1:
                    header, data = self.buffer.split('\r\n\r\n', 1)
                    for line in header.split("\r\n")[1:]:
                        key, value = line.split(": ", 1)
                        headers[key] = value

                    headers["Location"] = ("ws://%s%s" % (headers["Host"], self.path))
                    key = headers['Sec-WebSocket-Key']
                    token = b64encode(hashlib.sha1(str.encode(str(key + self.GUID))).digest())

                    handshake = "HTTP/1.1 101 Switching Protocols\r\n" \
                                "Upgrade: websocket\r\n" \
                                "Connection: Upgrade\r\n" \
                                "Sec-WebSocket-Accept: " + bytes.decode(token) + "\r\n" \
                                                                                 "WebSocket-Origin: " + str(
                        headers["Origin"]) + "\r\n" \
                                             "WebSocket-Location: " + str(headers["Location"]) + "\r\n\r\n"

                    self.conn.send(str.encode(str(handshake)))
                    self.handshaken = True
                    print('Socket%s Handshaken with %s success!' % (self.index, self.remote))
                    sendMessage('Welcome, ' + self.name + ' !')

            else:
                msg = decode(self.conn.recv(1024))
                if msg == 'quit':
                    print('Socket%s Logout!' % (self.index))
                    nowTime = time.strftime('%H:%M:%S', time.localtime(time.time()))
                    sendMessage('%s %s say: %s' % (nowTime, self.remote, self.name + ' Logout'))
                    deleteconnection(str(self.index))
                    self.conn.close()
                    break
                else:
                    print('Socket%s Got msg:%s from %s!' % (self.index, msg, self.remote))
                    nowTime = time.strftime('%H:%M:%S', time.localtime(time.time()))
                    sendMessage(msg)

            self.buffer = ""


class WebSocketServer(object):
    def __init__(self):
        self.socket = None

    def begin(self):
        print('WebSocketServer Start!')
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(("127.0.0.1", 12345))
        self.socket.listen(50)

        global connectionlist

        i = 0
        while True:
            connection, address = self.socket.accept()

            username = address[0]
            newSocket = WebSocket(connection, i, username, address)
            newSocket.start()
            connectionlist['connection' + str(i)] = connection
            i = i + 1


if __name__ == "__main__":
    server = WebSocketServer()
    server.begin()