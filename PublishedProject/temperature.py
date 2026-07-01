import numpy as np
import math

# https://www.fs.usda.gov/rm/pubs_series/rmrs/gtr/rmrs_gtr371.pdf

def Sinv(x):
    return -(0.7*x)/(0.3*x-1)

# shape = (10,10)

# sur_to_density = np.full(shape, 12240.0)
# density = np.full(shape, 420.0)
# load = np.full(shape, 0.313)
# qv = np.full(shape, 0.2)
# Mx = np.full(shape, 0.3)

def returnMassTemp(sur_to_density, density, load, qv, Mx):
    '''Input in SI Units.'''

    shape = density.shape
    sur_to_density /= 3.28084
    density /= 16.02
    load *= 0.204816

    rM = qv/Mx
    bed_depth = load/density

    a = 133*(sur_to_density**(-0.8189))
    max_re = sur_to_density**(1.5) * (495 + 0.0594*(sur_to_density**1.5))**-1
    op_pack = 3.348*sur_to_density**(-0.8189)
    pack = op_pack * 0.8
    rM = qv/Mx

    re = max_re*((pack/op_pack)**a)*np.exp(a*(np.ones(shape) - (pack/op_pack)))
    wn = load * (1-0.0555)
    nM = np.ones(shape) - 2.59*(rM) + 5.11 * (rM)**2 - 3.52*(rM)**3
    nS = np.full(shape, 0.174*0.01**(-0.19))

    dM = np.maximum(0, re*wn*nM*nS*0.00755987)
    c = 1
    area = math.pi*(0.381**2)/4
    Tm = (450-150)*Sinv((dM)/(0.2*area*1))+150
    Tm = np.minimum(450,np.maximum(Tm, 0))

    return dM, Tm

# print(returnMassTemp(sur_to_density, density, load, qv, Mx))
