# Volatility Surface Modeling

This is a backend Flask server that queries the Binance options API and calculates both natural and raw SVI parameterization of a selected asset and expiry.


## Endpoints

- **/api/option_chain**: Returns the options chain for a given underlying asset and expiration date in JSON format.
- **/api/assets**: Returns a list of available options assets along with their spot prices. 
- **/api/strikes**: Returns a list of available strikes for a given asset, expiry, and side. Side defaults to all if no side is given.
- **/api/svi_curve**: Calculates the svi paramterization for a given asset, expiry, side, and paramterization type. Returns a list of SVI points, SVI paramters, and the selected paramterization type.  


### Built With

* [![Python][Python]][Python-url]
* [![Flask][Flask]][Flask-url]
* [![SciPy][SciPy]][SciPy-url]
* [![NumPy][NumPy]][NumPy-url]

## Getting Started

To get a local server up and running follow these simple steps.

### Pre-requisites

- Python3 (3.12.3 or later)
- pip

### Installation

1. Clone this repository:
   ```bash
   git clone git@github.com:afan2g/vol-surface-modeling.git
    ```
2. Install python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the development server:
   ```bash
   python3 app.py
   ```
4. Success! Your server is hosted at `http://localhost:5000`.

### Access API

You can access the server data using [vol-surface-frontend](https://github.com/afan2g/vol-surface-frontend/)


## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact
Aaron Fan - af3623@columbia.edu

Project Link: [https://github.com/afan2g/vol-surface-modeling](https://github.com/afan2g/vol-surface-modeling)

## Acknowledgements
- [This post for explaining implied volatility, options pricing, and SVI parameterization](https://quant.stackexchange.com/questions/76366/option-pricing-for-illiquid-case)

- [Arbitrage-free SVI volatility surfaces, J Gatheral, 2004](https://mfe.baruch.cuny.edu/wp-content/uploads/2013/01/OsakaSVI2012.pdf)

- [crpyto-volatility-surface](https://github.com/joshuapjacob/crypto-volatility-surface)



[NumPy]: https://img.shields.io/badge/NumPy-4DABCF?logo=numpy&logoColor=fff
[NumPy-url]: https://numpy.org/
[SciPy]: https://img.shields.io/badge/scipy%20-00599C?style=flat&logo=scipy&logoColor=white
[SciPy-url]: https://scipy.org/
[Flask]: https://img.shields.io/badge/Flask-000?logo=flask&logoColor=fff
[Flask-url]: https://flask.palletsprojects.com/en/stable/
[Python]: https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff
[Python-url]: https://www.python.org/