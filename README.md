# AIS Serial ke MQTT

`decode.py` membaca AIVDM/AIVDO dari port serial, menampilkan hasil decode di
terminal, dan (jika `MQTT_HOST` diatur) mengirim ke MQTT.

## Pembagian file

- `serial_ais.py`: pembaca serial sederhana, menampilkan data mentah tanpa decode/MQTT.
- `decode.py`: pembaca serial, penggabungan fragmen, validasi posisi, filter,
  dan hasil decode AIS di terminal.
- `mqtt_publisher.py`: konfigurasi broker (termasuk username/password dan TLS),
  koneksi, format data posisi, dan publish ketiga topik.
- `deploy/install_latte.sh` dan `deploy/ais-jrc.service`: installer Linux
  dan layanan yang berjalan otomatis saat boot.
- `deploy/add_subscriber.sh`: pembuatan akun broker baca-saja untuk penerima data.
- `test_decode.py`: pengujian alur AIS dan publisher tanpa perangkat serial
  maupun broker sungguhan.
- `requirements.txt`: daftar dependensi Python.

## Topik MQTT

Publisher mengirim data ke tiga topik:

| Topik | Isi |
| --- | --- |
| `ais/aivdm/raw` | Satu kalimat NMEA `!AIVDM,...` apa adanya per fragmen, termasuk pesan yang gagal di-decode |
| `ais/aivdo/position` | JSON `{"received_at":"...","mmsi":123456789,"lat":-6.2,"lon":106.8}` dari AIVDO dengan koordinat valid |
| `ais/messages/decoded` | JSON hasil decode AIVDM/AIVDO (format sama dengan output terminal) |

Topik posisi hanya dikirim ketika AIVDO berisi posisi valid. Filter `--type`,
`--mmsi`, `--msg-type`, `--position-only`, dan `--bbox` berlaku untuk topik
`ais/messages/decoded` dan output terminal; pesan mentah AIVDM dan posisi AIVDO tetap
diterbitkan tanpa filter. Pesan multipart diterbitkan per fragmen di topik
mentah dan sekali setelah lengkap di topik decode. Semua publish memakai QoS 1,
tanpa retained message; pesan baru yang diterima saat broker terputus dilewati
(tidak di-buffer).

Jika sebelumnya sudah ada subscriber, perbarui topik lama:
`ais/raw/aivdm` menjadi `ais/aivdm/raw`, `ais/position/own` menjadi
`ais/aivdo/position`, dan `ais/decoded` menjadi `ais/messages/decoded`.

## Menjalankan

```sh
python3 -m pip install -r requirements.txt
export MQTT_HOST=broker.example.com
export MQTT_PORT=1883
export MQTT_USERNAME=ais_serial
export MQTT_PASSWORD='<password yang didaftarkan di broker>'
python3 decode.py --port /dev/ttyUSB0 --baudrate 38400
```

Daftarkan akun `ais_serial` beserta password-nya di broker terlebih dahulu;
pengaturan di aplikasi ini tidak membuat akun broker. Simpan password yang
sebenarnya di environment atau secret manager, bukan di kode, README, atau
berkas yang dibagikan. `MQTT_HOST` harus diisi dengan alamat broker yang bisa
diakses dari komputer AIS maupun komputer subscriber.

Host dan port juga bisa diatur dengan `--mqtt-host` dan `--mqtt-port`. Untuk
broker TLS, gunakan `MQTT_TLS=1` dan `MQTT_PORT=8883` (atau `--mqtt-tls` dan
`--mqtt-port 8883`). Gunakan TLS bila broker diakses melalui jaringan yang
tidak tepercaya agar username/password tidak dikirim tanpa enkripsi. Jika
`MQTT_HOST` tidak diatur, decoder tetap berjalan tanpa MQTT. Username dan
password wajib diisi saat MQTT diaktifkan; keduanya tidak dicetak di terminal.

## Instalasi di Latte (Debian/Ubuntu)

Pasang perangkat USB-serial AIS, lalu jalankan di Latte. Gunakan IP statis atau
nama DNS Latte yang benar-benar dapat diakses penerima data (nama ini
dimasukkan ke sertifikat TLS):

```sh
git clone https://github.com/ArifMunawarr/ais_jrc.git
cd ais_jrc
sudo bash deploy/install_latte.sh --broker-host 192.168.1.50
```

`--device` opsional jika hanya satu USB-serial terpasang di
`/dev/serial/by-id/`. Jika ada beberapa perangkat atau tidak ada symlink di
direktori itu, tambahkan `--device /dev/ttyUSB0` (sesuaikan portnya). Installer
akan meminta password akun `ais_serial` secara
tersembunyi di terminal; masukkan password yang sudah disepakati. Password
tidak perlu dimasukkan ke perintah, repo, atau file konfigurasi contoh.
Installer ini harus dijalankan **di Latte**, bukan di komputer pengembang.

Installer memasang Mosquitto dengan autentikasi dan TLS pada port `8883`,
membuat sertifikat CA lokal, menyiapkan virtualenv di `/opt/ais-jrc`, dan
mendaftarkan `ais-jrc.service`. Layanan memakai broker lokal (`localhost:8883`).
Kredensial layanan disimpan di `/etc/ais-jrc/ais.env` (hanya root dan grup
`ais-jrc` yang dapat membaca); password broker disimpan sebagai hash oleh
Mosquitto. Broker tidak mengizinkan klien anonim. Jika mengulang instalasi,
masukkan password yang sama atau bagikan password baru kepada pihak terkait.

Aturan udev installer membuat `/dev/ais` untuk perangkat yang dipilih, dengan
izin `dialout:0660`. Jika adapter memiliki serial unik, aturan mengikuti
identitas adapter; jika tidak, aturan mengikuti port fisik USB. Jangan pindah
port USB pada mode kedua. Pengguna layanan masuk grup `dialout`. Jika perangkat
tidak terpasang saat boot, layanan mencoba kembali setelah 10 detik.

```sh
ls -l /dev/ais
systemctl status mosquitto ais-jrc
journalctl -u ais-jrc -f
```

Port `8883/tcp` perlu diizinkan di firewall **hanya untuk jaringan/klien yang
dipercaya**, tidak dibuka ke internet publik tanpa perlindungan tambahan.
Sertifikat CA publik untuk subscriber ada di `/etc/ais-jrc/ca.crt`; kirim
berkas tersebut dan verifikasi sidik jari SHA-256 melalui jalur tepercaya.
Jika IP/nama broker berubah, jalankan lagi installer dengan `--broker-host`
baru untuk memperbarui sertifikat server dengan CA yang sama.

## Untuk pihak yang subscribe

Berikan alamat broker, port, pilihan TLS, dan daftar tiga topik di atas kepada
pihak penerima data. Buat akun broker **terpisah dengan izin baca saja** untuk
subscriber; akun `ais_serial` dipakai oleh publisher. Di Latte, buat akun
subscriber baru (password diminta oleh skrip):

```sh
sudo bash deploy/add_subscriber.sh penerima_ais
```

ACL broker mengizinkan publisher menulis tiga topik dan subscriber hanya
membaca topik AIS. Untuk penerima, atur `MQTT_HOST` ke IP/nama yang digunakan
di `--broker-host`, `MQTT_PORT=8883`, `MQTT_TLS=1`,
`MQTT_CA_CERTS=/lokasi/ca.crt`, serta `MQTT_SUB_USERNAME` dan
`MQTT_SUB_PASSWORD` dari akun baca-saja. Contoh dengan `paho-mqtt`:

```python
import os
import paho.mqtt.client as mqtt

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(
    os.environ["MQTT_SUB_USERNAME"], os.environ["MQTT_SUB_PASSWORD"]
)
if os.getenv("MQTT_TLS") == "1":
    client.tls_set(ca_certs=os.environ["MQTT_CA_CERTS"])

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"Koneksi MQTT ditolak: {reason_code}")
        return
    client.subscribe("ais/#", qos=1)

def on_message(client, userdata, message):
    print(message.topic, message.payload.decode("utf-8", errors="replace"))

client.on_connect = on_connect
client.on_message = on_message
client.connect(os.environ["MQTT_HOST"], int(os.getenv("MQTT_PORT", "1883")))
client.loop_forever()
```

Untuk menerima satu jenis data saja, ganti `ais/#` dengan nama topik pada tabel.
Subscriber baru hanya menerima pesan yang dikirim setelah ia terhubung;
publisher tidak menyimpan riwayat maupun retained message. Untuk histori,
subscriber perlu menyimpan pesan yang diterima ke penyimpanan sendiri.

Untuk menguji tanpa perangkat/broker:

```sh
python3 -m unittest -v test_decode
```
