import requests
from concurrent.futures import ThreadPoolExecutor
import time
from scipy.stats import norm
from scipy.optimize import curve_fit
import math
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_compress import Compress
import numpy as np
from svi_no_arbitrage import SVINoArbitrage
from apscheduler.schedulers.background import BackgroundScheduler
import logging
class Binance:
    def __init__(self, proxy=None):
        self.derivatives_base_endpoint = "https://eapi.binance.com"
        self.spot_base_endpoint = "https://api.binance.com"
        self.endpoints = {
            "time": self.derivatives_base_endpoint+"/eapi/v1/time",
            "ping": self.derivatives_base_endpoint+"/eapi/v1/ping",
            "info": self.derivatives_base_endpoint+"/eapi/v1/exchangeInfo",
            "orderbook": self.derivatives_base_endpoint+"/eapi/v1/depth",
            "mark": self.derivatives_base_endpoint+"/eapi/v1/mark",
            "open_interest": self.derivatives_base_endpoint+"/eapi/v1/openInterest",
            "spot": self.spot_base_endpoint+"/api/v3/ticker/price",
        }

        self.proxies = {
            "http": proxy,
            "https": proxy
        }

        self.market_info = {}
        self.option_markets = {}
        self.spot_prices = {}
        self.underlyings = {}
        self.expiry_dates = {}
        self.options_info = {}
        self.option_card_data = {}
        self.cur_time = time.time() * 1000
        self.last_exchange_update = None
        self.last_options_update = None
        self.last_spot_update = None
        self.session = requests.Session()
        self.scheduler = BackgroundScheduler()
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_exchange = executor.submit(self.get_exchange_info)
            future_spot = executor.submit(self.get_spot_markets) 
            future_options = executor.submit(self.get_options_info)
            
            # Wait for all to complete
            exchange_result = future_exchange.result()
            spot_result = future_spot.result()
            options_result = future_options.result()
        self.parse_options()
        self.parse_iv_info()
        self.scheduler.add_job(self.refresh_spot_options,"interval", seconds=5)
        self.scheduler.start()
    
    def get_spot_markets(self):
        """
        Get spot markets
        :return: Spot markets
        """
        response = self.session.get(self.endpoints['spot'], proxies=self.proxies)
        data = response.json()
        for item in data:
            symbol = item['symbol']
            price = float(item['price'])
            self.spot_prices[symbol] = price
        self.last_spot_update = int(round(time.time() * 1000))
        return self.spot_prices

    def get_options_info(self):
        """
        Get mark price for a symbol
        :param symbol: Symbol to get mark price for
        :return: Mark price
        """
        response = self.session.get(self.endpoints['mark'], proxies=self.proxies)
        self.last_options_update = int(round(time.time() * 1000))
        self.options_info = response.json()
        return self.options_info

    def parse_options(self):
        """
        Get option symbols
        :return: Option symbols
        """
        info = self.market_info

        for symbol in info['optionSymbols']:
            expiry_timestamp, underlying, strike_price = symbol['expiryDate'], symbol['underlying'], symbol['strikePrice']
            asset, expiry, strike, side = symbol['symbol'].split('-')
            time_diff_ms = expiry_timestamp - self.cur_time
            days_to_expiry = time_diff_ms / (1000 * 60 * 60 * 24)
            self.underlyings[asset] = underlying
            if asset not in self.option_markets:
                self.option_markets[asset] = {}
            if expiry not in self.option_markets[asset]:
                self.option_markets[asset][expiry] = {'C': [], 'P': []}
            self.option_markets[asset][expiry][side].append({
                "symbol": symbol['symbol'],
                "side": side,
                "strikePrice": float(strike_price),
                "expiry": expiry_timestamp,
                "time_to_expiry_ms": expiry_timestamp - self.cur_time,
                "days_to_expiry": (expiry_timestamp - self.cur_time) / (1000 * 60 * 60 * 24),
                "time_to_expiry": days_to_expiry/365.25,
                "underlying": underlying,
            })
            if asset not in self.expiry_dates:
                self.expiry_dates[asset] = set()
            self.expiry_dates[asset].add((expiry, expiry_timestamp))
        for asset in self.option_markets:
            for expiry in self.option_markets[asset]:
                self.option_markets[asset][expiry]['C'] = sorted(self.option_markets[asset][expiry]['C'], key=lambda x: x['strikePrice'])
                self.option_markets[asset][expiry]['P'] = sorted(self.option_markets[asset][expiry]['P'], key=lambda x: x['strikePrice'])
            self.expiry_dates[asset] = sorted(self.expiry_dates[asset], key=lambda x: x[1])
        return self.underlyings, self.option_markets

    def get_exchange_info(self):
        """
        Get market info
        :return: Market info
        """
        if len(self.market_info) == 0:
            response = self.session.get(self.endpoints['info'], proxies=self.proxies)

            self.market_info = response.json()
        self.last_exchange_update = self.market_info["serverTime"]
        return self.market_info
    
    def get_endpoint(self, endpoint, params=None):
        """
        Get endpoint
        :param endpoint: Endpoint to get
        :return: Endpoint
        """
        response = self.session.get(self.endpoints[endpoint], params=params, proxies=self.proxies)
        return response.json()
    
    def parse_iv_info(self):
        mark_info = self.options_info
        for data in mark_info:
            symbol = data['symbol']
            mark_price = float(data['markPrice'])
            mark_iv = float(data['markIV'])
            risk_free_rate = float(data['riskFreeInterest'])
            asset, expiry, strike, side = symbol.split('-')
            idx = self.find_mark_index(asset, expiry, float(strike), side)
            if idx is not None:
                option = self.option_markets[asset][expiry][side][idx]
                underlying = option['underlying']
                strike_price = option['strikePrice']
                spot_price = self.spot_prices[underlying]
                spot_price, strike_price = map(float, (spot_price, strike_price))
                time_to_expiry = float(option['time_to_expiry'])
                implied_volatility = float(mark_iv)
                total_implied_variance = float(implied_volatility)**2 * time_to_expiry
                forward_price = spot_price * math.exp(risk_free_rate * time_to_expiry)
                mark_data = {
                    'mark_price': mark_price,
                    'mark_iv': mark_iv,
                    'risk_free_rate': risk_free_rate,
                    'log_moneyness': math.log(forward_price/strike_price),
                    'moneyness': forward_price/strike_price,
                    'total_implied_variance': total_implied_variance,
                    'forward_price': forward_price,
                }
                self.option_markets[asset][expiry][side][idx].update(mark_data)
                self.option_markets[asset][expiry]['timeToExpiry'] = time_to_expiry 
                self.option_markets[asset][expiry]['forwardPrice'] = forward_price 
                self.option_markets[asset][expiry]['riskFreeRate'] = risk_free_rate 
                
    

    def find_mark_index(self, asset, expiry, strike, side):
        """
        Find mark index
        :param asset: Asset to find mark index for
        :param expiry: Expiry to find mark index for
        :param strike: Strike to find mark index for
        :param side: Side to find mark index for
        :return: Mark index
        """
        if asset not in self.option_markets:
            return None
        if expiry not in self.option_markets[asset]:
            return None
        if side not in self.option_markets[asset][expiry]:
            return None
        options_list = self.option_markets[asset][expiry][side]
        if not options_list:
            return None
        l,r = 0, len(self.option_markets[asset][expiry][side]) - 1
        target = strike
        while l <= r:
            mid = (l + r) // 2
            mid_strike = options_list[mid]['strikePrice']
            if mid_strike == target:
                return mid
            elif mid_strike < target:
                l = mid + 1
            else:
                r = mid - 1
        return None
    def filter_options(self, asset=None, expiry=None, side=None):
        """
        Filter options
        :param asset: Asset to filter options for
        :param expiry: Expiry to filter options for
        :param side: Side to filter options for
        :return: Filtered options
        """
        if asset not in self.option_markets:
            return self.option_markets
        if expiry is None:
            return self.option_markets[asset]
        if side is None:
            return self.option_markets[asset][expiry]
        return self.option_markets[asset][expiry][side]
    



    def calculate_option_price(self, S, K, T, r, sigma, option_type='C'):
        """
        Calculate Black-Scholes option price.
        :param S: Spot price
        :param K: Strike price
        :param T: Time to maturity (in years)
        :param r: Risk-free interest rate
        :param sigma: Volatility
        :param option_type: 'C' for Call, 'P' for Put
        :return: Option price as float
        """
        S, K, T, r, sigma = map(float, (S, K, T, r, sigma))
        sqrtT = math.sqrt(T)
        d1 = (math.log(S/K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrtT)
        d2 = d1 - sigma * sqrtT

        if option_type == 'C':
            return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
        elif option_type == 'P':
            return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        else:
            raise ValueError("Invalid option type. Use 'C' for call and 'P' for put.")
        
        return price
            
    def get_option_chain(self, asset, expiry, side):
        """
        Display option chain
        :param asset: Asset to display option chain for
        :param expiry: Expiry to display option chain for
        :param side: Side to display option chain for
        :return: Option chain
        """
        if asset not in self.option_markets:
            return None
        if expiry not in self.option_markets[asset]:
            return None
        if side not in self.option_markets[asset][expiry] and side != 'A':
            return None
        res = {}
        if side == 'A':
            call_options = self.option_chain(asset, expiry, 'C')
            put_options = self.option_chain(asset, expiry, 'P')
            res = {'C': call_options, 'P': put_options}
        else:
            chain = self.option_chain(asset, expiry, side)
            res = {side: chain}
        res['lastOptionUpdate'] = self.last_options_update
        res['lastExchangeUpdate'] = self.last_exchange_update
        res['asset'] = asset
        res['expiry'] = expiry
        res['timeToExpiry'] = self.option_markets[asset][expiry]['timeToExpiry']
        res['forwardPrice'] = self.option_markets[asset][expiry]['forwardPrice']
        res['riskFreeRate'] = self.option_markets[asset][expiry]['riskFreeRate']
        res['spotPrice'] = self.spot_prices[self.underlyings[asset]]
        return res
    
    def option_chain(self, asset, expiry, side):
        """
        Display option chain
        :param asset: Asset to display option chain for
        :param expiry: Expiry to display option chain for
        :param side: Side to display option chain for
        :return: Option chain
        """
        options_list = self.option_markets[asset][expiry][side]
        res = []
        for option in options_list:
            symbol = option['symbol']
            mark_price = option['mark_price']
            mark_iv = option['mark_iv']
            risk_free_rate = option['risk_free_rate']
            strike_price = option['strikePrice']
            time_to_expiry = option['time_to_expiry']
            days_to_expiry = option['days_to_expiry']
            moneyness = option['moneyness']
            log_moneyness = option['log_moneyness']
            side = option['side']
            spot_price = float(self.spot_prices[option['underlying']])
            bsm_price = self.calculate_option_price(spot_price, strike_price, time_to_expiry, risk_free_rate, mark_iv, side)
            forward_price = option['forward_price']
            append_data = {
                'symbol': symbol,
                'strikePrice': strike_price,
                'markPrice': mark_price,
                'impliedVolatility': mark_iv,
                'riskFreeRate': risk_free_rate,
                'timeToExpiry': time_to_expiry,
                'daysToExpiry': days_to_expiry,
                'moneyness': moneyness,
                'logMoneyness': log_moneyness,
                'spotPrice': spot_price,
                'bsmPrice': bsm_price,
                'forwardPrice': forward_price,
            }
            res.append(append_data)
        return res
    
    def moneyness_array(self, asset, expiry, side):
        if asset not in self.option_markets:
            return None
        if expiry not in self.option_markets[asset]:
            return None
        if side not in 'CPA':
            return None
        if side == 'A':
            call_options = self.option_markets[asset][expiry]['C']
            put_options = self.option_markets[asset][expiry]['P']
            options_list = call_options + put_options
        else:
            options_list = self.option_markets[asset][expiry][side]
        k = np.array([float(option['log_moneyness']) for option in options_list])
        total_implied_variances = np.array([float(option['total_implied_variance']) for option in options_list])
        return k, total_implied_variances
    
    def raw_svi(self, k, a, b, rho, m, sigma):
        """
        k = log moneyness
        returns: total implied variance (implied vol**2)*time to expiry
        """
        return a + b * (rho * (k - m) + np.sqrt((k - m)**2 + sigma**2))
    
    def natural_svi(self, k, delta, mu, rho, omega, zeta):
        return delta + (omega/2) * (1 + (zeta*rho*(k - mu)) + np.sqrt((zeta*(k-mu) + rho) ** 2 + (1 - rho**2)))
    


    def raw_svi_parameterization(self, asset, expiry, side):
        """
        Using svi_model function, we try to find the best-fit parameters a, b, rho, m, sigma that minimizes the difference between the model's calculated total implied variance and the actual total implied variance from the option chain.
        each option in the option chain comes pre-calculated with its own total implied variance.
        """
        k, total_implied_variances = self.moneyness_array(asset, expiry, side)
        
        fitter = SVINoArbitrage()
        params = fitter.constrained_svi_fit(k, total_implied_variances)

        is_valid, message = self.validate_no_arbitrage(asset, expiry, side, params)
        if not is_valid:
            return None
    
        return params
    
    def natural_svi_parameterization(self, asset, expiry, side):
        k, total_implied_variances = self.moneyness_array(asset, expiry, side)
        # Initial guess for the parameters delta, mu, rho, omega, zeta
        # initial_guess = [total_implied_variances.mean(), k.mean(), 0.0, 0.5, 0.1]
        # Bounds for the parameters delta, mu, rho, omega, zeta
        # delta: all real numbers, mu: all real numbers, rho: [-1, 1], omega >= 0, zeta > 0
        bounds = ([-np.inf, -np.inf, -0.999, 0, 0.001], 
                  [np.inf, np.inf, 0.999, np.inf, np.inf])
        
        initial_guesses = [
        [total_implied_variances.mean(), k.mean(), 0.0, 0.5, 0.1],
        [np.median(total_implied_variances), 0.0, 0.0, 0.3, 0.1],
        [total_implied_variances[len(total_implied_variances)//2], k.mean(), -0.3, 0.8, 0.2],
        ]
    
        for guess in initial_guesses:
            try:
                params, _ = curve_fit(self.natural_svi, k, total_implied_variances, p0=guess, bounds=bounds, maxfev=10000)
                predicted = self.natural_svi(k, *params)
                if np.all(predicted > 0): 
                    return params
            except:
                continue
        
        return None 
    
    def validate_no_arbitrage(self, asset, expiry, side, params):
        """
        Validate that SVI parameters satisfy no-arbitrage conditions.
        """
        a, b, rho, m, sigma = params
        
        # Check basic constraints
        if b < 0:
            return False, "b must be non-negative"
        if abs(rho) >= 1:
            return False, "|rho| must be < 1"
        if sigma <= 0:
            return False, "sigma must be positive"
        
        # Check b(1 + |rho|) <= 4
        if b * (1 + abs(rho)) > 4:
            return False, "b(1 + |rho|) > 4 violates no-arbitrage"
        
        # Check minimum variance
        w_min = a + b * sigma * np.sqrt(1 - rho**2)
        if w_min < 0:
            return False, "Minimum total variance is negative"
        
        # Check butterfly arbitrage at sample points
        k_data, _ = self.moneyness_array(asset, expiry, side)
        k_test = np.linspace(np.min(k_data) - 1, np.max(k_data) + 1, 50)
        
        for k in k_test:
            w = a + b * (rho * (k - m) + np.sqrt((k - m)**2 + sigma**2))
            if w < 0:
                return False, f"Negative total variance at k={k}"
        
        return True, "No arbitrage violations detected"
        
    def svi_jw_parameterization(self, asset, expiry, side):
        a, b, rho, m, sigma = self.raw_svi_parameterization(asset, expiry, side)
        # Convert raw SVI parameters to JW parameters
        t = self.option_markets[asset][expiry]['C'][0]['time_to_expiry'] if side == 'C' else self.option_markets[asset][expiry]['P'][0]['time_to_expiry']
        svi_params = self.raw_to_svi_jw(a, b, rho, m, sigma, t)
        return svi_params['vt'], svi_params['psit'], svi_params['pt'], svi_params['ct'], svi_params['vt_min']
    
    def get_svi_curve_points(self, asset, expiry, side, parameterization_type='raw'):
        """
        Get SVI curve points for a given asset, expiry, and side.
        :param asset: Asset to get SVI curve points for
        :param expiry: Expiry to get SVI curve points for
        :param side: Side to get SVI curve points for
        :return: SVI curve points
        """
        if parameterization_type not in ['raw', 'natural']:
            raise ValueError("Invalid parameterization type. Use 'raw' or 'natural'.")
        if parameterization_type == 'natural':
            params = self.natural_svi_parameterization(asset, expiry, side)
            if params is None:
                app.logger.error(f"Natural SVI parameterization failed for {asset}-{expiry}-{side}")
                return None
            delta, mu, rho, omega, zeta = params
        elif parameterization_type == 'raw':
            params = self.raw_svi_parameterization(asset, expiry, side)
            if params is None:
                app.logger.error(f"Raw SVI parameterization failed for {asset}-{expiry}-{side}")
                return None
            a, b, rho, m, sigma = params
        
        k = []
        if side == 'A':
            call_options = self.option_markets[asset][expiry]['C']
            put_options = self.option_markets[asset][expiry]['P']
            options_list = call_options + put_options
            k = [float(option['log_moneyness']) for option in call_options + put_options]
        else:
            options_list = self.option_markets[asset][expiry][side]
            k = [float(option['log_moneyness']) for option in options_list]

        x_points = np.linspace(min(k)-0.1, max(k)+0.1, 100)  # Adjust range as needed
        if parameterization_type == 'natural':
            svi_values = self.natural_svi(x_points, delta, mu, rho, omega, zeta)
        elif parameterization_type == 'raw':
            svi_values = self.raw_svi(x_points, a, b, rho, m, sigma)
        points = []
        time_to_expiry = self.option_markets[asset][expiry]['C'][0]['time_to_expiry'] if side == 'C' else self.option_markets[asset][expiry]['P'][0]['time_to_expiry']
        forward_price = self.option_markets[asset][expiry]['C'][0]['forward_price'] if side == 'C' else self.option_markets[asset][expiry]['P'][0]['forward_price']
        implied_vols = np.sqrt(svi_values / time_to_expiry)  # Convert total implied variance to implied volatility
        spot_price = float(self.spot_prices[self.underlyings[asset]])
        risk_free_rate = self.option_markets[asset][expiry]['C'][0]['risk_free_rate'] if side == 'C' else self.option_markets[asset][expiry]['P'][0]['risk_free_rate']
        for k_val, iv in zip(x_points, implied_vols):
            moneyness = math.exp(k_val)
            strike = forward_price / moneyness
            call_premium = self.calculate_option_price(K=strike, T=time_to_expiry, r=risk_free_rate, option_type='C', S=spot_price, sigma=iv)
            put_premium = self.calculate_option_price(K=strike, T=time_to_expiry, r=risk_free_rate, option_type='P', S=spot_price, sigma=iv)
            points.append({
                'logMoneyness': float(k_val),
                'strikePrice': float(strike),
                'moneyness': float(moneyness),
                'impliedVolatility': float(iv),
                'callPremium': call_premium,
                'putPremium': put_premium
            })
        return (points, params.tolist())
    
    def refresh_exchange_info(self, minutes=60):
        now = int(round(time.time() * 1000))
        if(now - self.last_exchange_update) > (minutes * 60 * 1000): 
            self.get_exchange_info()

    def refresh_options_info(self, seconds=5):
        now = int(round(time.time() * 1000))
        if (now - self.last_options_update) > (seconds* 1000):
            self.get_options_info()
    
    def refresh_spot_info(self, seconds=5):
        now = int(round(time.time() * 1000))
        if (now - self.last_spot_update) > (seconds * 1000):
            self.get_spot_markets()

    def refresh_spot_options(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_spot = executor.submit(self.get_spot_markets) 
            future_options = executor.submit(self.get_options_info)
            
            # Wait for all to complete
            spot_result = future_spot.result()
            options_result = future_options.result()
        self.parse_iv_info()
    


app = Flask(__name__)
Compress(app)
CORS(app)
BinanceAPI = Binance()



@app.route('/api/option_chain', methods=['GET', 'POST'])
def get_option_chain():
    if request.method == 'POST':
        data = request.get_json()
        asset = data.get('asset')
        expiry = data.get('expiry')
        side = data.get('side')
    else:
        asset = request.args.get('asset')
        expiry = request.args.get('expiry')
        side = request.args.get('side')
    chain = BinanceAPI.get_option_chain(asset, expiry, side)
    return jsonify(chain)

@app.route('/api/assets', methods=['GET'])
def get_available_assets():
    assets = list(BinanceAPI.option_markets.keys())
    spot_prices = {}
    for asset in assets:
        spot_prices[asset] = BinanceAPI.spot_prices[BinanceAPI.underlyings[asset]]
    return jsonify({'assets': assets, 'spot_prices': spot_prices})

@app.route('/api/expiries', methods=['GET'])
def get_available_expiries():

        return jsonify(BinanceAPI.expiry_dates)
   

@app.route('/api/strikes', methods=['GET', 'POST'])
def get_available_strikes():
    if request.method == 'POST':
        data = request.get_json()
        asset = data.get('asset')
        expiry = data.get('expiry')
        side = data.get('side')
    else:
        asset = request.args.get('asset')
        expiry = request.args.get('expiry')
        side = request.args.get('side')
    if side == 'A':
        call_strikes = [option['strikePrice'] for option in BinanceAPI.option_markets[asset][expiry]['C']]
        put_strikes = [option['strikePrice'] for option in BinanceAPI.option_markets[asset][expiry]['P']]
        strikes = {'call': call_strikes, 'put': put_strikes}
    else:
        strikes = [option['strikePrice'] for option in BinanceAPI.option_markets[asset][expiry][side]]
    return jsonify({'strikes': strikes})


@app.route('/api/svi_curve', methods=['GET', 'POST'])
def get_svi_curve():
    if request.method == 'POST':
        data = request.get_json()
        asset = data.get('asset')
        expiry = data.get('expiry')
        side = data.get('side')
        parameterization_type = data.get('parameterization_type', 'raw')
    else:
        asset = request.args.get('asset')
        expiry = request.args.get('expiry')
        side = request.args.get('side')
        parameterization_type = request.args.get('parameterization_type', 'raw')
    try:
        result = BinanceAPI.get_svi_curve_points(asset, expiry, side, parameterization_type)
        if result is None:
            app.logger.error(f"SVI curve calculation returned None for {asset}-{expiry}-{side}-{parameterization_type}")
            return jsonify({'error': 'SVI parameterization failed - insufficient or invalid data'}), 400
        
        points, params = result
        
    except Exception as e:
        app.logger.error(f"Error calculating SVI curve: {e}")
        return jsonify({'error': 'Failed to calculate SVI curve'}), 500
    
    if points is None:
        app.logger.error(f"Error calculating SVI curve. No points returned: {e}")
        return jsonify({'error': 'Failed to calculate SVI curve'}), 500
    app.logger.info(f"{parameterization_type} paramterization params: {params}")
    return jsonify({'points': points, 'params': params, 'parameterization_type': parameterization_type})

@app.route('/api/refresh/spot_options', methods=["GET"])
def refresh_spot_options():
    try:
        BinanceAPI.refresh_spot_options()
    except Exception as e:
        app.logger.error(f"Error refreshing spot markets and options: {e}")
        return 500
    

@app.route("/")
def index():
    return "Hello from Flask on Render!"

if __name__ == "__main__":
    app.run(debug=True, port=5000)

if __name__ != '__main__':
    # Running under gunicorn
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)