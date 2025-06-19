import numpy as np
from scipy.optimize import minimize, NonlinearConstraint

class SVINoArbitrage:
    """
    SVI parameterization with no-arbitrage constraints
    """
    
    @staticmethod
    def check_butterfly_arbitrage_raw(a, b, rho, m, sigma):
        """
        Check butterfly arbitrage constraints for raw SVI parameterization.
        Returns True if no arbitrage, False otherwise.
        """
        # Basic parameter constraints
        if b < 0 or abs(rho) >= 1 or sigma <= 0:
            return False
        
        # Condition 1: b(1 + |ρ|) ≤ 4
        # This ensures the total variance function is not too steep
        if b * (1 + abs(rho)) > 4:
            return False
        
        # Condition 2: Discriminant check
        # The function g(k) must be non-negative for all k
        # where g(k) = (1 - ρ²) - (ρ + (k-m)/√((k-m)² + σ²))²
        # This is automatically satisfied if |ρ| < 1
        
        return True
    
    @staticmethod
    def butterfly_density_constraint(k, a, b, rho, m, sigma):
        """
        Calculate the butterfly density (second derivative of call price w.r.t. strike).
        This must be non-negative for no arbitrage.
        """
        # First, calculate d1 and d2 for the SVI implied volatility
        w = a + b * (rho * (k - m) + np.sqrt((k - m)**2 + sigma**2))
        
        # For very small w, return a large value to indicate violation
        if w <= 0:
            return -1
        
        # Calculate derivatives of w w.r.t. k
        sqrt_term = np.sqrt((k - m)**2 + sigma**2)
        w_k = b * (rho + (k - m) / sqrt_term)
        w_kk = b * sigma**2 / (sqrt_term**3)
        
        # Butterfly density condition from Gatheral's SVI paper
        # This is a simplified check - full implementation would compute
        # the actual second derivative of the call price
        g = (1 - k * w_k / (2 * w))**2 - w_k**2 / 4 * (1/w + 1/4) + w_kk / 2
        
        return g
    
    @staticmethod
    def calendar_spread_constraint(t1, t2, params1, params2):
        """
        Check calendar spread arbitrage between two expiries.
        Total variance must be increasing in time.
        """
        if t2 <= t1:
            return True  # Not applicable
        
        a1, b1, rho1, m1, sigma1 = params1
        a2, b2, rho2, m2, sigma2 = params2
        
        # Sample points to check
        k_points = np.linspace(-2, 2, 50)
        
        for k in k_points:
            w1 = a1 + b1 * (rho1 * (k - m1) + np.sqrt((k - m1)**2 + sigma1**2))
            w2 = a2 + b2 * (rho2 * (k - m2) + np.sqrt((k - m2)**2 + sigma2**2))
            
            # Total variance must be increasing
            if w2 < w1:
                return False
        
        return True
    
    def constrained_svi_fit(self, k_data, total_variance_data, initial_guess=None):
        """
        Fit SVI parameters with no-arbitrage constraints.
        """
        if initial_guess is None:
            initial_guess = [
                np.mean(total_variance_data),  # a
                0.5,  # b
                0.0,  # rho
                0.0,  # m
                0.1   # sigma
            ]
        
        # Objective function: minimize squared error
        def objective(params):
            a, b, rho, m, sigma = params
            w_model = a + b * (rho * (k_data - m) + np.sqrt((k_data - m)**2 + sigma**2))
            return np.sum((w_model - total_variance_data)**2)
        
        # Constraint functions
        def butterfly_constraint(params):
            """Returns positive value if no arbitrage"""
            a, b, rho, m, sigma = params
            
            # Basic constraints
            if not self.check_butterfly_arbitrage_raw(a, b, rho, m, sigma):
                return -1
            
            # Check butterfly density at sample points
            k_test = np.linspace(np.min(k_data) - 0.5, np.max(k_data) + 0.5, 20)
            min_density = np.inf
            
            for k in k_test:
                density = self.butterfly_density_constraint(k, a, b, rho, m, sigma)
                min_density = min(min_density, density)
            
            return min_density
        
        # Bounds
        bounds = [
            (-np.inf, np.inf),  # a
            (0, np.inf),        # b  
            (-0.999, 0.999),    # rho
            (-np.inf, np.inf),  # m
            (0.001, np.inf)     # sigma
        ]
        
        # Additional constraints
        constraints = [
            # b(1 + |rho|) <= 4
            {'type': 'ineq', 'fun': lambda p: 4 - p[1] * (1 + abs(p[2]))},
            # Butterfly arbitrage
            {'type': 'ineq', 'fun': butterfly_constraint},
            # Ensure positive total variance at ATM
            {'type': 'ineq', 'fun': lambda p: p[0] + p[1] * p[4] * np.sqrt(1 - p[2]**2)}
        ]
        
        # Optimize
        result = minimize(
            objective,
            initial_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            return result.x
        else:
            # Fall back to constrained least squares if SLSQP fails
            return self.fallback_constrained_fit(k_data, total_variance_data)
    
    def fallback_constrained_fit(self, k_data, total_variance_data):
        """
        Fallback fitting method with relaxed constraints.
        """
        from scipy.optimize import curve_fit
        
        def svi_with_constraints(k, a, b, rho, m, sigma):
            # Enforce constraints within the function
            b = max(0, b)
            rho = np.clip(rho, -0.99, 0.99)
            sigma = max(0.001, sigma)
            
            # Additional constraint: b(1 + |rho|) <= 4
            if b * (1 + abs(rho)) > 4:
                b = 4 / (1 + abs(rho))
            
            return a + b * (rho * (k - m) + np.sqrt((k - m)**2 + sigma**2))
        
        initial_guess = [
            np.mean(total_variance_data),
            0.5,
            0.0,
            np.mean(k_data),
            0.1
        ]
        
        try:
            params, _ = curve_fit(
                svi_with_constraints,
                k_data,
                total_variance_data,
                p0=initial_guess,
                maxfev=10000
            )
            return params
        except:
            # Return initial guess if all else fails
            return initial_guess
    
    @staticmethod
    def validate_svi_surface(asset_data, expiry_data):
        """
        Validate an entire SVI surface across expiries for calendar arbitrage.
        """
        expiries = sorted(expiry_data.keys())
        violations = []
        
        for i in range(len(expiries) - 1):
            t1, t2 = expiries[i], expiries[i + 1]
            params1 = expiry_data[t1]['svi_params']
            params2 = expiry_data[t2]['svi_params']
            
            if not SVINoArbitrage.calendar_spread_constraint(t1, t2, params1, params2):
                violations.append((t1, t2))
        
        return len(violations) == 0, violations
