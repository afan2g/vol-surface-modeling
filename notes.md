to calculate iv, given option price:
1. start with an estimate of iv, using Brenner and Subrahmanyam (1988) estimation: sigma0 = sqrt(2pi/T)*(C/S), where S=underlying price, C=call value, T=duration
2. Iteratively apply Newton-Raphson formula until sufficient accuracy: sigma_n+1 = sigma_n - ((BSM(sigma_n) - P)/vega(sigma_n)), where P=option price, BSM()=black-scholes-merton function, and vega can be derived from BSM.


To build a surface, you can use SVI:
1. Compute implied volatilities
2. build volatility surface using svi

vol surface: https://quant.stackexchange.com/questions/76366/option-pricing-for-illiquid-case
implied volatility calculation: https://quant.stackexchange.com/questions/7761/a-simple-formula-for-calculating-implied-volatility
https://quant.stackexchange.com/questions/73861/is-it-possible-to-have-only-one-volatility-surface-for-american-options-that-fi/73891#73891
SVI paramterization: https://quant.stackexchange.com/questions/49034/why-is-the-svi-parameterization-in-terms-of-variance
https://mfe.baruch.cuny.edu/wp-content/uploads/2013/01/OsakaSVI2012.pdf
