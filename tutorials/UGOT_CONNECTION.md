# Connecting to the UGOT Robot

This guide walks you through how to connect your laptop to the UGOT robot via its onboard hotspot.

---

## Step 1: Open Settings on the UGOT

On the UGOT's display, navigate to and tap **Settings**.

![Step 1 – Settings screen on the UGOT](images/hotspot/1.jpeg)
*The UGOT home screen with the Settings option highlighted.*

---

## Step 2: Enable the Hotspot

Inside Settings, tap **Hotspot** and toggle it **on**.

Make a note of:
- **Hotspot name** — this will be in the format `UGOT_XXXX`
- **Password** — you'll need this to connect your laptop in Step 5

![Step 2 – Hotspot screen with toggle enabled](images/hotspot/2.jpeg)
![Step 2 – Hotspot screen with toggle enabled](images/hotspot/3.jpeg)
*The Hotspot settings screen showing the network name and password.*

---

## Step 3: Navigate to "About"

Exit the Hotspot screen to return to **Settings**, then scroll down and tap **About**.

![Step 3 – Settings menu scrolled to show About](images/hotspot/4.jpeg)
*Scrolling down in Settings to find the About section.*

---

## Step 4: Find the UGOT's IP Address

Inside **About**, locate the robot's IP address. This is typically:

```
192.168.88.1
```

Make a note of this — you'll use it to communicate with the robot from your laptop.

![Step 4 – About screen showing the IP address](images/hotspot/5.jpeg)
*The About screen displaying the UGOT's IP address.*

---

## Step 5: Connect Your Laptop to the UGOT Hotspot

On your laptop, open your Wi-Fi settings and connect to the hotspot you noted in Step 2:

- **Network name:** `UGOT_XXXX`
- **Password:** *(the password from Step 2)*

![Step 5 – Laptop Wi-Fi settings showing the UGOT hotspot](images/hotspot/6.png)

*Connecting to the UGOT_XXXX network from the laptop's Wi-Fi menu.*

---

## You're Connected!

Once your laptop joins the `UGOT_XXXX` network, you can communicate with the robot using the IP address found in Step 4 (e.g. `192.168.88.1`).

> **Tip:** If you can't connect, double-check that the hotspot is still toggled on and that you're using the correct password.
