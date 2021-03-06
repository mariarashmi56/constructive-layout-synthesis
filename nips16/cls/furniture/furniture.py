# -*- encoding: utf-8 -*-

import pymzn
import numpy as np

from cls.utils import freeze, input_x, input_star_x
from cls.coactive import Problem


class Furniture(Problem):
    """Problem for coactive furniture arrangement.

    Parameters
    ----------
    canvas_size : positive int
        The size of the canvas.
    num_tables : positive int
        The number of tables.
    """

    infer_model = 'cls/furniture/infer.mzn'
    improve_model = 'cls/furniture/improve.mzn'
    phi_model = 'cls/furniture/phi.mzn'

    def __init__(self, canvas_size=12, num_tables=8, layout=0, timeout=None,
                 **kwargs):
        num_features = 10
        super().__init__(num_features)

        layouts = [
        {
            'door_x': [7, 4],
            'door_y': [1, canvas_size],
            'N_WALLS': 2,
            'wall_x': [1, 8],
            'wall_y': [1, canvas_size - 2],
            'wall_dx': [5, 5],
            'wall_dy': [6, 3]
        },
        {
        }
        ]

        self.timeout = timeout
        self._data = {'SIDE': canvas_size, 'N_TABLES': num_tables,
                      **layouts[layout]}
        self._phis = {}
        self._debug = kwargs['debug']


    def phi(self, x):
        _frx = freeze(x)
        if _frx in self._phis:
            return self._phis[_frx]

        _phi = pymzn.minizinc(self.phi_model,
                              data={**self._data, **input_x(x)},
                              output_vars=['phi'], serialize=True,
                              mzn_globals_dir='opturion-cpx', keep=True,
                              fzn_fn=pymzn.opturion)[0]['phi']
        self._phis[_frx] = np.array(_phi)
        return self._phis[_frx]

    def infer(self, w, approx=False):
        sols = []
        if approx and self.timeout:
            timeout = self.timeout
        else:
            timeout = None
        while len(sols) == 0:
            sols =  pymzn.minizinc(self.infer_model,
                                   data={**self._data, 'w': w},
                                   output_vars=['x', 'y', 'dx', 'dy'],
                                   mzn_globals_dir='opturion-cpx',
                                   serialize=True, keep=True, 
                                   fzn_fn=pymzn.opturion, timeout=timeout)
            if timeout is not None:
                timeout *= 2
        return sols[-1]

    def improve(self, x, x_star, w, alpha=0.2, approx=False):
        try:
            sols = []
            if approx and self.timeout:
                timeout = self.timeout
            else:
                timeout = None
            while len(sols) == 0:
                sols = pymzn.minizinc(self.improve_model,
                                      data={**self._data, **input_x(x), 'w': w,
                                            **input_star_x(x_star),
                                            'ALPHA': alpha},
                                      output_vars=['x', 'y', 'dx', 'dy'],
                                      mzn_globals_dir='opturion-cpx',
                                      serialize=True, keep=True,
                                      fzn_fn=pymzn.opturion, timeout=timeout)
                if timeout is not None:
                    timeout *= 2
            return sols[-1]
        except pymzn.MiniZincUnsatisfiableError:
            # when no improvement possible for noisy users
            return x

