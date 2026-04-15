<div align="center">

# 🇵🇱 Polskie Obligacje Skarbowe
**Home Assistant integration for Polish Treasury Bonds**

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/MarcinSachs/obligacje-ha?style=flat-square)](https://github.com/MarcinSachs/obligacje-ha)
![GitHub stars](https://img.shields.io/github/stars/MarcinSachs/obligacje-ha?style=flat-square)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MarcinSachs&repository=obligacje-ha&category=Integration)

[Repository](https://github.com/MarcinSachs/obligacje-ha) · [Issues](https://github.com/MarcinSachs/obligacje-ha/issues)

---

</div>

## ✨ Overview
Track the current value, profit/loss, earned interest, and maturity status for your Polish Treasury Bonds directly in Home Assistant.

This integration supports multiple bond positions and automatically fetches market data for reliable portfolio monitoring.

---

## 🔧 Key Features

- 📊 Multiple bond positions with separate series, quantity, and purchase details
- ⚙️ Seven sensors per position:
  - Current value (PLN)
  - Purchase value (PLN)
  - Profit / Loss (PLN)
  - Current interest rate (%)
  - Accrued interest (PLN)
  - Maturity date
  - Days until maturity
- 🧠 Automatic data retrieval from Polish Treasury bond sources
- 🌐 Uses GUS CPI and NBP reference rate for accurate calculations
- ✅ UI-based configuration with Home Assistant Config Flow

---

## 🛠 Installation

### Option 1: HACS (Recommended)
The easiest way to install and stay updated.

[![Open your Home Assistant instance and open a repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MarcinSachs&repository=obligacje-ha&category=Integration)

1. Click the button above or go to **HACS** → **Integrations**.
2. Add a custom repository: `https://github.com/MarcinSachs/obligacje-ha`.
3. Install the integration.
4. Restart Home Assistant.

### Option 2: Manual installation
1. Copy the `custom_components/obligacje` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Add the integration through **Settings** → **Devices & Services** → **Add Integration** and search for **Polskie Obligacje Skarbowe**.

---

## ⚙️ Configuration

Each integration entry corresponds to a single bond position.

Required fields:
- **Series code** (e.g. `EDO0130`)
- **Quantity** (each bond is 100 PLN)

Optional fields:
- **Purchase date** (`YYYY-MM-DD`) — if omitted, the integration estimates it from the series code.

Add one entry per bond holding to monitor all positions independently.

---

## 📋 Available Sensors

| Category | Sensors |
| :--- | :--- |
| **Value** | Current value, Purchase value, Profit / Loss |
| **Interest** | Current interest rate, Accrued interest |
| **Maturity** | Maturity date, Days until maturity |

---

## 📝 Notes

- This integration is designed for Polish Treasury Bonds only.
- Values are updated automatically based on external Polish financial data sources.

---

## 📎 Resources

- GitHub: https://github.com/MarcinSachs/obligacje-ha
- Issues: https://github.com/MarcinSachs/obligacje-ha/issues

---

<div align="center">
Developed with ❤️ by <a href="https://github.com/MarcinSachs">Marcin Sachs</a>
</div>