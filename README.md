# obligacje-ha

# Polskie Obligacje Skarbowe (Polish Treasury Bonds) Home Assistant Integration

This custom integration for Home Assistant allows you to track the value, interest, and other parameters of Polish Treasury Bonds directly in your Home Assistant dashboard.

## Features

- Supports multiple bond positions (each with its own series, quantity, and optional purchase date)
- Automatic data fetching and calculation for each position
- Seven sensors per position:
	- Current value (PLN)
	- Purchase value (PLN)
	- Profit / Loss (PLN)
	- Current interest rate (%)
	- Accrued interest (PLN)
	- Maturity date
	- Days until maturity
- Configuration via Home Assistant UI (Config Flow)
- Data sources: obligacjeskarbowe.pl, GUS (CPI), NBP (reference rate)

## Installation

1. Copy the `custom_components/obligacje` directory to your Home Assistant `custom_components` folder.
2. Restart Home Assistant.
3. Add the integration via the Home Assistant UI (Integrations page → Add Integration → search for "Polskie Obligacje Skarbowe").

## Configuration

Each entry represents a single bond position:
- **Series code** (e.g., `EDO0130`)
- **Quantity** (number of bonds, each = 100 PLN)
- **Purchase date** (optional, YYYY-MM-DD; if omitted, estimated from series code)

You can add as many positions as you have.

## Documentation

- [GitHub repository](https://github.com/MarcinSachs/obligacje-ha)
- [Issue tracker](https://github.com/MarcinSachs/obligacje-ha/issues)

## License

MIT