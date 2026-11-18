# AIS JRC Serial ke MQTT

Program ini membaca kalimat `!AIVDM` dan `!AIVDO` dari receiver AIS JRC melalui
USB-serial, menampilkan hasil decode, lalu menerbitkannya ke broker MQTT di
Latte. Broker, service pembaca, dan aturan nama perangkat dipasang otomatis di
Latte; tidak ada sertifikat TLS yang perlu diatur untuk pemakaian LAN.

## Hasil yang dipasang di Latte

- `ais-jrc.service` berjalan otomatis saat boot dan membaca `/dev/ais`.
- Mosquitto aktif di port `1883`, menolak klien anonim, dan memakai ACL.
- `ais_serial` hanya boleh **menulis** data AIS.
- `ais_reader` hanya boleh **membaca** data AIS; dipakai untuk MQTT Explorer
  atau aplikasi penerima.
- `/dev/ais` adalah nama tetap untuk USB-serial AIS dengan izin
  `dialout:0660`.
- Program dipasang di `/opt/ais-jrc`; konfigurasi service tersimpan terbatas di
  `/etc/ais-jrc/ais.env`.

## Topik MQTT

| Topik | Isi |
| --- | --- |
| `ais/aivdm/raw` | Satu kalimat NMEA `!AIVDM,...` apa adanya per fragmen |
| `ais/aivdo/position` | JSON `{"received_at":"...","mmsi":123456789,"lat":-6.2,"lon":106.8}` dari AIVDO dengan posisi valid |
| `ais/messages/decoded` | JSON hasil decode AIVDM lengkap |

Semua publish memakai QoS 1, tanpa retained message. Subscriber hanya menerima
pesan yang dikirim setelah ia tersambung; broker tidak menyimpan riwayat.
Posisi AIVDO hanya dipublish jika `lat` dan `lon` valid.

## Persyaratan Latte

- Debian/Ubuntu dengan `systemd`, `apt`, dan `udev`.
- Hak `sudo` dan koneksi jaringan untuk `apt` serta `pip` saat instalasi awal.
- USB-serial AIS sudah terpasang.
- IP Latte tetap/statik dan bisa diakses komputer penerima.
- Jika Mosquitto sudah punya konfigurasi lain di `/etc/mosquitto/conf.d`,
  installer berhenti agar tidak menimpa konfigurasi yang ada.

## Instalasi sampai jalan di Latte

### 1. Pasang perangkat dan cek port

```sh
ls -l /dev/serial/by-id/
hostname -I
```

Jika tidak ada entri di `/dev/serial/by-id`, cek `/dev/ttyUSB*` atau
`/dev/ttyACM*` yang muncul saat adapter dipasang.

### 2. Ambil kode

```sh
git clone https://github.com/ArifMunawarr/ais_jrc.git
cd ais_jrc
```

### 3. Jalankan installer

Ganti `192.168.1.50` dengan IP Latte yang sebenarnya:

```sh
sudo bash deploy/install_latte.sh --broker-host 192.168.1.50
```

Jika ada lebih dari satu USB-serial atau tidak ada symlink di
`/dev/serial/by-id`, tambahkan perangkat AIS yang benar:

```sh
sudo bash deploy/install_latte.sh --broker-host 192.168.1.50 \
    --device /dev/ttyUSB0
```

Installer akan meminta dua password di terminal; ketiknya lalu tekan Enter.
Karakternya tidak akan tampil:

1. `Password broker untuk ais_serial`
2. `Password subscriber untuk ais_reader`

Masukkan password yang sudah disepakati masing-masing. Password tidak perlu
ditulis ke perintah, kode, atau README. Installer hanya menyimpan password
publisher di `/etc/ais-jrc/ais.env` untuk service dan menyimpan hash password
broker di Mosquitto.

### 4. Verifikasi instalasi

```sh
ls -l /dev/ais
systemctl status mosquitto ais-jrc
ss -lptn | grep 1883
journalctl -u ais-jrc -f
```

Hasil yang diharapkan:

- `/dev/ais` mengarah ke perangkat serial AIS.
- `mosquitto` dan `ais-jrc` berstatus `active (running)`.
- Mosquitto mendengarkan `1883`.
- Log `ais-jrc` menampilkan data decode atau pesan koneksi MQTT.

Jika perangkat dicabut dan dipasang lagi, `/dev/ais` harus tetap muncul
(mengikuti serial adapter jika ada, atau port USB fisik jika adapter tidak punya
serial). Jika perangkat belum ada saat boot, service mencoba lagi setiap
10 detik.

### 5. Uji MQTT dari Latte

```sh
sudo apt install -y mosquitto-clients
mosquitto_sub -h localhost -p 1883 \
    -u ais_reader -P '<password ais_reader>' \
    -t 'ais/#' -F '%I %t %p'
```

Untuk melihat satu topik:

```sh
mosquitto_sub -h localhost -p 1883 -u ais_reader \
    -P '<password ais_reader>' -t 'ais/aivdo/position'
```

## Melihat dari Mac dengan MQTT Explorer

Pastikan Mac dan Latte berada di jaringan yang sama, lalu buat koneksi baru:

- **Host:** IP Latte yang dipakai pada `--broker-host`
- **Port:** `1883`
- **Username:** `ais_reader`
- **Password:** password `ais_reader` yang dimasukkan saat instalasi
- **Encryption/TLS:** nonaktif
- **Validate certificate / CA:** tidak perlu
- **Subscription/topic:** `ais/#`

`ais/#` menampilkan ketiga topik. Untuk satu jenis data, subscribe hanya ke
`ais/aivdm/raw`, `ais/aivdo/position`, atau `ais/messages/decoded`.

## Membatasi akses jaringan

MQTT di mode ini tidak terenkripsi, jadi username, password, dan data dapat
terbaca di jaringan. Gunakan hanya pada LAN tepercaya. Broker mendengarkan di
semua antarmuka; batasi akses `1883/tcp` di firewall ke IP penerima, jangan
teruskan port ke internet, dan pisahkan jaringan AIS dari Wi-Fi publik. Contoh
dengan UFW, jika UFW dipakai:

```sh
sudo ufw allow from 192.168.1.20 to any port 1883 proto tcp
sudo ufw status numbered
```

Ganti `192.168.1.20` dengan IP komputer penerima.

## Akun subscriber tambahan

Jika pihak lain juga akan subscribe, buat akun baca-saja terpisah. Password
diminta oleh skrip:

```sh
cd ais_jrc
sudo bash deploy/add_subscriber.sh penerima_ais
```

Jangan membagikan akun `ais_serial` kepada penerima; akun itu untuk service
publisher dan hanya boleh menulis.

## Perintah operasional

```sh
systemctl status mosquitto ais-jrc      # status layanan
journalctl -u ais-jrc -f                # log pembaca AIS
journalctl -u mosquitto -f              # log broker
sudo systemctl restart ais-jrc          # restart pembaca
sudo systemctl restart mosquitto        # restart broker
ls -l /dev/ais                          # nama perangkat tetap
```

Jika repo diperbarui, dari Latte:

```sh
cd ais_jrc
git pull
sudo bash deploy/install_latte.sh --broker-host 192.168.1.50
```

Masukkan password yang sama saat diminta, atau beri tahu pihak terkait jika
password diubah. Installer menimpa file konfigurasi broker milik paket ini dan
mengaktifkan ulang layanan.

## Menjalankan manual untuk pengembangan

```sh
python3 -m pip install -r requirements.txt
export MQTT_HOST=192.168.1.50
export MQTT_PORT=1883
export MQTT_USERNAME=ais_serial
export MQTT_PASSWORD='<password broker>'
python3 decode.py --port /dev/ttyUSB0 --baudrate 38400
```

Filter output decode: `--type`, `--mmsi`, `--msg-type`, `--position-only`, dan
`--bbox`. `ais/aivdm/raw` dan `ais/aivdo/position` tetap dipublish tanpa filter;
filter hanya berlaku untuk output terminal dan `ais/messages/decoded`. AIVDO
tidak dipublish ke `ais/messages/decoded` agar tidak ganda dengan topik posisi. TLS tetap
didukung untuk broker lain dengan `MQTT_TLS=1`, `MQTT_PORT=8883`, dan
`MQTT_CA_CERTS=/lokasi/ca.crt`.

Untuk tes tanpa perangkat/broker:

```sh
python3 -m unittest -v test_decode
```

## Pembagian file

- `serial_ais.py`: pembaca serial sederhana, menampilkan data mentah tanpa decode/MQTT.
- `decode.py`: pembaca serial, penggabungan fragmen, validasi posisi, filter,
  dan hasil decode AIS di terminal.
- `mqtt_publisher.py`: konfigurasi broker, autentikasi, dan publish tiga topik.
- `deploy/install_latte.sh` dan `deploy/ais-jrc.service`: installer Linux dan
  layanan yang berjalan otomatis saat boot.
- `deploy/add_subscriber.sh`: pembuatan akun broker baca-saja tambahan.
- `test_decode.py`: pengujian alur AIS dan publisher tanpa perangkat/broker.
- `requirements.txt`: daftar dependensi Python.
