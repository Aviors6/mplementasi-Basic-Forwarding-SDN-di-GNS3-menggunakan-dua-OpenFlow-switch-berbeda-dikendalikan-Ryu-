# 🌐 SDN Basic Forwarding — OVS & MikroTik CHR + Ryu Controller (OpenFlow 1.0)

> **Implementasi Basic Forwarding SDN di GNS3 menggunakan dua OpenFlow switch berbeda vendor
> yang dikendalikan satu Ryu Controller terpusat.**

Proyek ini membuktikan bahwa satu **Ryu Controller** dapat menginstall flow rule ke
**Open vSwitch** (DPID=1) dan **MikroTik RouterOS/CHR** (DPID=2) secara bersamaan
menggunakan OpenFlow 1.0, sehingga dua host (H1 dan H2) dapat saling berkomunikasi
melewati dua switch berbeda vendor tanpa konfigurasi manual di masing-masing switch.

![OpenFlow](https://img.shields.io/badge/OpenFlow-1.0-green)
![Python](https://img.shields.io/badge/Python-2.7-yellow)
![Platform](https://img.shields.io/badge/Platform-GNS3-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## 🗺️ Topologi

```
MANAGEMENT PLANE — 10.10.10.0/24
┌────────────────────────────────────────────────────┐
│  Ryu-Controller       OVS-1          MikroTik-CHR  │
│  (10.10.10.10)    (10.10.10.1)      (10.10.10.2)  │
│        │                │                 │        │
│        └────────────────┴─────────────────┘        │
│                      Switch1 (GNS3)                │
└────────────────────────────────────────────────────┘

DATA PLANE — 10.0.0.0/24
  H1 (10.0.0.1)          OVS              MikroTik         H2 (10.0.0.2)
       │          eth1 ┌──────┐ eth2  ether2 ┌──────┐ ether3      │
       └───────────────┤DPID=1├───────────────┤DPID=2├────────────┘
                       └──────┘               └──────┘

Flow yang diinstall Ryu:
  OVS      : in_port=1 → output:2      |  in_port=2 → output:1
  MikroTik : in_port=1 → SET_DL_DST(H2_MAC), output:2
             in_port=2 → SET_DL_DST(H1_MAC), output:1
```

> Penjelasan kenapa MikroTik memerlukan MAC Rewrite ada di bagian [Kendala & Solusi](#-kendala--solusi).

---

## 📌 Daftar Perangkat & IP Address

| Perangkat | Interface | IP Address | Keterangan |
|---|---|---|---|
| Ryu-Controller-1 | eth0 | `10.10.10.10/24` | SDN Controller |
| OpenvSwitch-1 | eth0 | `10.10.10.1/24` | Management |
| OpenvSwitch-1 | eth1 / eth2 | — | OF Port 1 → H1 / OF Port 2 → MikroTik |
| MikroTikCHR | ether1 | `10.10.10.2/24` | Management |
| MikroTikCHR | ether2 / ether3 | — | OF Port 1 → OVS / OF Port 2 → H2 |
| MikroTikCHR | ether4 | `192.168.100.2/24` | Winbox / Cloud |
| AlpineLinux-1 (H1) | eth0 | `10.0.0.1/24` | Host 1 |
| AlpineLinux-2 (H2) | eth0 | `10.0.0.2/24` | Host 2 |

### MAC Address Penting (Sesuaikan dengan Environment GNS3 Anda)

| Interface | MAC Address |
|---|---|
| H1 eth0 | `02:42:99:39:3a:00` |
| H2 eth0 | `02:42:36:01:7b:00` |
| MikroTik ether2 | `0c:48:12:37:00:01` |
| MikroTik ether3 | `0c:48:12:37:00:02` |

> ⚠️ Wajib cek ulang MAC dengan `ip addr show eth0` (H1/H2) dan `/interface print` (MikroTik)
> sebelum mengisi script, karena GNS3 bisa generate MAC yang berbeda.

---

## 🛠️ Software yang Digunakan

| Software | Versi | Fungsi |
|---|---|---|
| GNS3 | 2.x | Network Emulator |
| Ryu Controller | 4.x | SDN Controller |
| Python | 2.7 | Runtime Ryu |
| Open vSwitch | 2.x | OpenFlow Switch (DPID=1) |
| MikroTik RouterOS CHR | 6.49.18 | OpenFlow Switch (DPID=2) |
| MikroTik OpenFlow Package | 6.49.18 | Plugin OpenFlow (install terpisah) |
| AlpineLinux | 3.x | End Host |
| Wireshark | 3.x | Packet Analysis |

---


## 🚀 Menjalankan Proyek

### Prasyarat

Sebelum memulai, pastikan:
- GNS3 sudah berjalan dengan topologi sesuai diagram di atas
- Package `openflow` sudah terinstall di MikroTik CHR
- Ryu sudah terinstall (`pip install ryu --break-system-packages`)
- File `ofp_handler.py` sudah dipatch (lihat langkah persiapan di `docs/USER_MANUAL.md`)

### Urutan Startup Setiap Buka GNS3

```
1. Start semua node di GNS3

2. Ryu Controller
   sh /root/start_ryu.sh

3. Open vSwitch
   sh /root/start_ovs.sh

4. MikroTik (console RouterOS)
   /openflow print              ← cek status "connected"
   Jika belum connected:
   /openflow disable mt-of
   /openflow enable mt-of

5. H1 (AlpineLinux-1)
   sh /root/start_h1.sh

6. H2 (AlpineLinux-2)
   sh /root/start_h2.sh

7. Test ping dari H1
   ping 10.0.0.2
```

---

## ⚙️ Konfigurasi Singkat Per Node

### Ryu Controller

```bash
# Set IP lalu jalankan controller
ip addr add 10.10.10.10/24 dev eth0 && ip link set eth0 up
ryu-manager --ofp-tcp-listen-port 6633 /root/ryu_basic_forwarding_of10.py
```

### Open vSwitch

```bash
# Buat bridge dengan DPID terkunci dan arahkan ke controller
ovs-vsctl add-br br0
ovs-vsctl set bridge br0 other-config:datapath-id=0000000000000001
ovs-vsctl set bridge br0 protocols=OpenFlow10
ovs-vsctl set-fail-mode br0 secure
ovs-vsctl add-port br0 eth1 -- set interface eth1 ofport_request=1
ovs-vsctl add-port br0 eth2 -- set interface eth2 ofport_request=2
ovs-vsctl set-controller br0 tcp:10.10.10.10:6633
# eth0 TIDAK dimasukkan ke bridge — management only
```

### MikroTik RouterOS CHR

```routeros
/ip address add address=10.10.10.2/24 interface=ether1
/ip firewall connection tracking set enabled=no
/openflow add name=mt-of controller=10.10.10.10 datapath-id=0/00:00:00:00:00:02 disabled=no
/openflow port add disabled=no switch=mt-of interface=ether2
/openflow port add disabled=no switch=mt-of interface=ether3
# ether1 dan ether4 TIDAK dimasukkan ke OpenFlow port
```

### H1 dan H2

```bash
# H1
ip addr add 10.0.0.1/24 dev eth0 && ip link set eth0 up
arp -s 10.0.0.2 0c:48:12:37:00:01   # static ARP ke MAC ether2 MikroTik

# H2
ip addr add 10.0.0.2/24 dev eth0 && ip link set eth0 up
arp -s 10.0.0.1 0c:48:12:37:00:02   # static ARP ke MAC ether3 MikroTik
```

---

## 🔍 Verifikasi

```bash
# OVS — cek flow terinstall dan counter naik saat ping
ovs-ofctl -O OpenFlow10 dump-flows br0
ovs-vsctl show
```

```routeros
# MikroTik — cek flow dan statistik port
/openflow print
/openflow flow print stats
/openflow port print stats
```

---

## ⚠️ Kendala & Solusi

### Masalah

Forward path (H1→H2) berjalan normal, namun **return path (H2→H1) gagal total** —
counter `inport=2` di MikroTik selalu 0 meskipun Wireshark membuktikan paket dari H2
keluar dari eth0-nya.

### Root Cause

MikroTik CHR 6.49 **tidak mengaktifkan promiscuous mode** di interface yang menjadi
OpenFlow port. Akibatnya, NIC ether3 membuang semua frame unicast yang bukan miliknya:

```
H2 kirim ARP reply → dst MAC = H1 MAC
ether3 MAC         = 0c:48:12:37:00:02
ether3 cek: bukan MAC saya, bukan broadcast → BUANG ❌
```

### Solusi — Static ARP + MAC Rewrite

Paksa H1 dan H2 mengirim frame ke MAC MikroTik (bukan ke MAC satu sama lain),
lalu Ryu merewrite dst MAC di dalam flow sebelum diteruskan ke tujuan:

```
H2 → dst MAC = ether3 MAC ✅ (ether3 terima)
OpenFlow: SET_DL_DST = H1 MAC → output ke ether2
H1 terima frame dengan dst MAC = H1 MAC ✅
```

---

## 📊 Hasil Pengujian

| Skenario | Hasil |
|---|---|
| Ryu connect ke OVS (DPID=1) | ✅ |
| Ryu connect ke MikroTik (DPID=2) | ✅ |
| Flow terinstall di OVS | ✅ 2 flow |
| Flow terinstall di MikroTik | ✅ 2 flow |
| Ping H1 → H2 (forward path) | ✅ |
| Ping H2 → H1 (return path tanpa fix) | ❌ |
| Ping H2 → H1 (return path dengan MAC rewrite) | ✅ |

---


<div align="center">

*Panduan lengkap step-by-step ada di [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md)*

</div>
