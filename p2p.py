import socket  # นำเข้าไลบรารี socket เพื่อใช้ในการสร้างการเชื่อมต่อเครือข่าย
import threading  # นำเข้าไลบรารี threading เพื่อใช้ในการทำงานแบบหลายเธรด
import json  # นำเข้าไลบรารี json เพื่อใช้ในการแปลงข้อมูลเป็นรูปแบบ JSON
import sys  # นำเข้าไลบรารี sys เพื่อใช้ในการจัดการกับอาร์กิวเมนต์ของโปรแกรม
import os  # นำเข้าไลบรารี os เพื่อใช้ในการทำงานกับระบบไฟล์
import secrets  # นำเข้าไลบรารี secrets เพื่อใช้ในการสร้างข้อมูลสุ่มที่ปลอดภัย

""" การรันโปรแกรมบนสองเครื่อง:
บนเครื่องแรก: python p2p_node.py 5000
บนเครื่องที่สอง: python p2p_node.py 5001
ใช้ตัวเลือกที่ 1 บนเครื่องใดเครื่องหนึ่งเพื่อเชื่อมต่อกับอีกเครื่อง """

class Node:
    def __init__(self, host, port):
        self.host = host  # กำหนด host
        self.port = port  # กำหนด port
        self.peers = []  # ใช้ในการเก็บ socket ของ peer ที่เชื่อมต่อ
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # สร้าง socket TCP
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # กำหนดค่าให้สามารถนำ socket กลับมาใช้ใหม่ได้
        self.transactions = []  # เก็บ transactions
        self.transaction_file = f"transactions_{port}.json"  # บันทึก transactions ในไฟล์ตามพอร์ต
        self.wallet_address = self.generate_wallet_address()  # สร้าง wallet address ในโหนดนี้

    def generate_wallet_address(self):
        # สร้าง wallet address แบบง่าย
        return '0x' + secrets.token_hex(20)  # สร้างที่อยู่กระเป๋าเงินแบบสุ่ม

    def start(self):
        # เริ่มการทำงานของโหนด
        self.socket.bind((self.host, self.port))  # ผูก socket กับ host และ port
        self.socket.listen(1)  # เริ่มฟังการเชื่อมต่อใหม่
        print(f"Node listening on {self.host}:{self.port}")  # แสดงข้อความว่ากำลังฟังการเชื่อมต่อ
        print(f"Your wallet address is: {self.wallet_address}")  # แสดงที่อยู่กระเป๋าเงิน

        self.load_transactions()  # โหลด transactions จากไฟล์ (ถ้ามี)

        # เริ่ม thread รับการเชื่อมต่อใหม่
        accept_thread = threading.Thread(target=self.accept_connections)  # สร้าง thread ใหม่เพื่อรับการเชื่อมต่อใหม่
        accept_thread.start()  # เริ่ม thread ที่สร้างขึ้น

    def accept_connections(self):
        while True:
            # รอรับการเชื่อมต่อใหม่
            client_socket, address = self.socket.accept()  # ยอมรับการเชื่อมต่อใหม่
            print(f"New connection from {address}")  # แสดงข้อความเมื่อมีการเชื่อมต่อใหม่

            # เริ่ม thread ใหม่เพื่อจัดการการเชื่อมต่อนี้
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))  # สร้าง thread ใหม่เพื่อจัดการการเชื่อมต่อนี้
            client_thread.start()  # เริ่ม thread ที่สร้างขึ้น

    def handle_client(self, client_socket):
        while True:
            try:
                # รับข้อมูลจาก client
                data = client_socket.recv(1024)  # รับข้อมูลจาก client
                if not data:
                    break  # ถ้าไม่มีข้อมูลให้หยุดการเชื่อมต่อ
                message = json.loads(data.decode('utf-8'))  # แปลงข้อมูลที่ได้รับเป็น JSON
                
                self.process_message(message)  # ประมวลผลข้อความที่ได้รับ

            except Exception as e:
                print(f"Error handling client: {e}")  # แสดงข้อความเมื่อเกิดข้อผิดพลาด
                break  # หยุดการเชื่อมต่อ

        client_socket.close()  # ปิดการเชื่อมต่อ

    def connect_to_peer(self, peer_host, peer_port):
        try:
            # สร้างการเชื่อมต่อไปยัง peer
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # สร้าง socket ใหม่
            peer_socket.connect((peer_host, peer_port))  # เชื่อมต่อไปยัง peer
            self.peers.append(peer_socket)  # เพิ่ม socket ที่เชื่อมต่อไปยังลิสต์ peers
            print(f"Connected to peer {peer_host}:{peer_port}")  # แสดงข้อความเมื่อเชื่อมต่อกับ peer สำเร็จ

            # เริ่ม thread รับข้อมูลจาก peer นี้
            peer_thread = threading.Thread(target=self.handle_client, args=(peer_socket,))  # สร้าง thread ใหม่เพื่อรับข้อมูลจาก peer นี้
            peer_thread.start()  # เริ่ม thread ที่สร้างขึ้น

        except Exception as e:
            print(f"Error connecting to peer: {e}")  # แสดงข้อความเมื่อเกิดข้อผิดพลาดในการเชื่อมต่อ

    def broadcast(self, message):
        # ส่งข้อมูลไปยังทุก peer ที่เชื่อมต่ออยู่
        for peer_socket in self.peers:
            try:
                peer_socket.send(json.dumps(message).encode('utf-8'))  # ส่งข้อความในรูปแบบ JSON
            except Exception as e:
                print(f"Error broadcasting to peer: {e}")  # แสดงข้อความเมื่อเกิดข้อผิดพลาดในการส่งข้อความ
                self.peers.remove(peer_socket)  # ลบ peer ที่เกิดข้อผิดพลาดออกจากลิสต์

    def process_message(self, message):
        # ประมวลผลข้อความที่ได้รับ
        if message['type'] == 'transaction':
            print(f"Received transaction: {message['data']}")  # แสดงข้อความเมื่อได้รับธุรกรรม
            self.add_transaction(message['data'])  # เพิ่มธุรกรรมใหม่
        else:
            print(f"Received message: {message}")  # แสดงข้อความที่ได้รับ

    def add_transaction(self, transaction):
        # เพิ่ม transaction ใหม่และบันทึกลงไฟล์
        self.transactions.append(transaction)  # เพิ่มธุรกรรมใหม่ไปยังลิสต์
        self.save_transactions()  # บันทึกธุรกรรมลงไฟล์
        print(f"Transaction added and saved: {transaction}")  # แสดงข้อความเมื่อบันทึกธุรกรรมสำเร็จ

    def create_transaction(self, recipient, amount):
        # สร้าง transaction ใหม่
        transaction = {
            'sender': self.wallet_address,  # ผู้ส่งคือกระเป๋าเงินของโหนดนี้
            'recipient': recipient,  # ผู้รับ
            'amount': amount  # จำนวนเงิน
        }
        self.add_transaction(transaction)  # เพิ่มธุรกรรมใหม่ไปยังลิสต์
        self.broadcast({'type': 'transaction', 'data': transaction})  # ส่งธุรกรรมไปยังทุก peer

    def save_transactions(self):
        # บันทึก transactions ลงไฟล์
        with open(self.transaction_file, 'w') as f:  # เปิดไฟล์ในโหมดเขียน
            json.dump(self.transactions, f)  # บันทึกธุรกรรมในรูปแบบ JSON

    def load_transactions(self):
        # โหลด transactions จากไฟล์ (ถ้ามี)
        if os.path.exists(self.transaction_file):  # ตรวจสอบว่าไฟล์มีอยู่หรือไม่
            with open(self.transaction_file, 'r') as f:  # เปิดไฟล์ในโหมดอ่าน
                self.transactions = json.load(f)  # โหลดธุรกรรมในรูปแบบ JSON
            print(f"Loaded {len(self.transactions)} transactions from file.")  # แสดงจำนวนธุรกรรมที่โหลดได้

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python p2p.py <port>")  # แสดงข้อความวิธีการใช้โปรแกรม
        sys.exit(1)  # ออกจากโปรแกรม
    
    port = int(sys.argv[1])  # กำหนดพอร์ตจากอาร์กิวเมนต์ที่ได้รับ
    node = Node("0.0.0.0", port)  # ใช้ "0.0.0.0" เพื่อรับการเชื่อมต่อจากภายนอก
    node.start()  # เริ่มการทำงานของโหนด
    
    while True:
        print("\n1. Connect to a peer")  # แสดงตัวเลือกในการเชื่อมต่อกับ peer
        print("2. Create a transaction")  # แสดงตัวเลือกในการสร้างธุรกรรมใหม่
        print("3. View all transactions")  # แสดงตัวเลือกในการดูธุรกรรมทั้งหมด
        print("4. View my wallet address")  # แสดงตัวเลือกในการดูที่อยู่กระเป๋าเงิน
        print("5. Exit")  # แสดงตัวเลือกในการออกจากโปรแกรม
        choice = input("Enter your choice: ")  # รับตัวเลือกจากผู้ใช้
        
        if choice == '1':
            peer_host = input("Enter peer host to connect: ")  # รับที่อยู่โฮสต์ของ peer
            peer_port = int(input("Enter peer port to connect: "))  # รับพอร์ตของ peer
            node.connect_to_peer(peer_host, peer_port)  # เชื่อมต่อกับ peer
        elif choice == '2':
            recipient = input("Enter recipient wallet address: ")  # รับที่อยู่กระเป๋าเงินของผู้รับ
            amount = float(input("Enter amount: "))  # รับจำนวนเงิน
            node.create_transaction(recipient, amount)  # สร้างธุรกรรมใหม่
        elif choice == '3':
            print("All transactions:")  # แสดงธุรกรรมทั้งหมด
            for tx in node.transactions:
                print(tx)  # พิมพ์ธุรกรรมแต่ละรายการ
        elif choice == '4':
            print(f"Your wallet address is: {node.wallet_address}")  # แสดงที่อยู่กระเป๋าเงิน
        elif choice == '5':
            break  # ออกจากลูป
        else:
            print("Invalid choice. Please try again.")  # แสดงข้อความเมื่อผู้ใช้เลือกตัวเลือกที่ไม่ถูกต้อง

    print("Exiting...")  # แสดงข้อความเมื่อออกจากโปรแกรม
