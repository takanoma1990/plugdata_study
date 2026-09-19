import math
import time

from pythonosc.udp_client import SimpleUDPClient

IP = "127.0.0.1"   # 同じPCの中で送る場合は localhost
PORT = 8000        # plugdata の [netreceive -u -b 8000] と揃える

client = SimpleUDPClient(IP, PORT)

# 連続した値を送る
# 0〜1 をゆっくり往復させる。1秒間に約30回送る。
print("送信中です。Ctrl+C で終了します。")
t = 0.0
try:
    while True:
        x = (math.sin(t) + 1) / 2          # 0〜1
        y = (math.cos(t * 0.7) + 1) / 2    # 0〜1
        client.send_message("/x", float(x))
        client.send_message("/y", float(y))
        t += 0.05
        time.sleep(1 / 30) # 送りすぎないように間隔をあける
except KeyboardInterrupt:
    print("終了しました。")
