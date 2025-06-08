from scipy.stats import norm
'''
Notation:

'''
class SVI:
    def __init__(self, a, b, rho, m, sigma):
        self.a = a
        self.b = b
        self.rho = rho
        self.m = m
        self.sigma = sigma
    
    def raw_svi(self, k):
        """
        Calculate the SVI volatility for a given strike price k.
        """
        # Calculate the SVI parameters
        a = self.a
        b = self.b
        rho = self.rho
        m = self.m
        sigma = self.sigma
        
        # Calculate the SVI volatility
        v = a + b * (rho * (k - m) + ((1 - rho**2) ** 0.5) * sigma)
        
        return v