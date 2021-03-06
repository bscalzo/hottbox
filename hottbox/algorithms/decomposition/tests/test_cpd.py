"""
Tests for the cpd module
"""
import pytest
import sys
import io
import numpy as np
from functools import reduce
from ..cpd import *
from ....core.structures import Tensor, TensorCPD


class TestBaseCPD:
    """ Tests for BaseCPD class """

    def test_init(self):
        """ Tests for constructor of BaseCPD class """
        # Even though we can create such object we shouldn't do that
        default_params = dict(init='svd',
                              max_iter=50,
                              epsilon=10e-3,
                              tol=10e-5,
                              random_state=None,
                              mode_description='mode_description',
                              verbose=False
                              )

        # basically for coverage tests object of
        with pytest.raises(NotImplementedError):
            tensor = Tensor(np.arange(2))
            rank = 5
            base_cpd = BaseCPD(**default_params)
            base_cpd.decompose(tensor, rank)
        with pytest.raises(NotImplementedError):
            base_cpd = BaseCPD(**default_params)
            base_cpd.plot()


class TestCPD:
    """ Tests for CPD class """

    def test_init(self):
        """ Tests for the constructor of CPD algorithm """
        init = 'svd'
        max_iter = 50
        epsilon = 10e-3
        tol = 10e-5
        mode_description = 'mode_description'
        verbose = False
        cpd = CPD(init=init,
                  max_iter=max_iter,
                  epsilon=epsilon,
                  tol=tol,
                  mode_description=mode_description,
                  verbose=verbose)
        assert not cpd.cost         # check that this list is empty
        assert cpd.name == CPD.__name__
        assert cpd.init == init
        assert cpd.max_iter == max_iter
        assert cpd.epsilon == epsilon
        assert cpd.tol == tol
        assert cpd.mode_description == mode_description
        assert cpd.verbose == verbose

    def test_copy(self):
        """ Tests for copy method """
        cpd = CPD()
        cpd.cost = [1, 2]
        cpd_copy = cpd.copy()

        assert cpd_copy is not cpd
        assert cpd_copy.name == cpd.name
        assert cpd_copy.init == cpd.init
        assert cpd_copy.max_iter == cpd.max_iter
        assert cpd_copy.epsilon == cpd.epsilon
        assert cpd_copy.tol == cpd.tol
        assert cpd_copy.mode_description == cpd.mode_description
        assert cpd_copy.verbose == cpd.verbose
        assert cpd_copy.cost != cpd.cost

        cpd.init = 'qwerty'
        cpd.max_iter += 1
        cpd.epsilon += 1
        cpd.tol += 1
        cpd.mode_description = 'qwerty'
        cpd.verbose = not cpd.verbose
        cpd.cost = [3, 4]
        assert cpd_copy.init != cpd.init
        assert cpd_copy.max_iter != cpd.max_iter
        assert cpd_copy.epsilon != cpd.epsilon
        assert cpd_copy.tol != cpd.tol
        assert cpd_copy.mode_description != cpd.mode_description
        assert cpd_copy.verbose != cpd.verbose
        assert cpd.cost != cpd_copy.cost

    def test_init_fmat(self):
        """ Tests for _init_fmat method """
        np.random.seed(0)
        shape = (4, 5, 6)
        size = reduce(lambda x, y: x * y, shape)
        tensor = Tensor(np.random.randn(size).reshape(shape))
        cpd = CPD()

        # ------ tests that cpd.cost is reset each time _init_fmat is called
        cpd.cost = [1, 2, 3]
        rank = (min(tensor.shape)-1,)
        cpd._init_fmat(tensor=tensor, rank=rank)
        assert not cpd.cost

        # ------ tests on getting factor matrices of the correct shape
        for rank_value in range(min(tensor.shape)-1, max(tensor.shape)+2):
            rank = (rank_value,)
            fmat = cpd._init_fmat(tensor=tensor, rank=rank)
            for mode, mat in enumerate(fmat):
                assert mat.shape == (tensor.shape[mode], rank_value)

        # ------ tests for the type of initialisation
        # svd type initialisation should produce factor matrices with orthogonal columns
        rank = (min(tensor.shape)-1,)
        cpd = CPD(init='svd')
        fmat = cpd._init_fmat(tensor=tensor, rank=rank)
        for mat in fmat:
            result = np.dot(mat.T, mat)
            true_result = np.eye(rank[0])
            np.testing.assert_almost_equal(result, true_result)

        # svd type initialisation but the `rank` is greater then one of the dimensions then you get random fmat
        # and there would be a runtime warning
        rank = (min(tensor.shape)+1,)
        cpd = CPD(init='svd', verbose=True)
        with pytest.warns(RuntimeWarning):
            fmat = cpd._init_fmat(tensor=tensor, rank=rank)
        for mat in fmat:
            result_1 = np.dot(mat.T, mat)
            result_2 = np.eye(rank[0])
            # since each mat is randomly initialized it is not orthonormal
            with pytest.raises(AssertionError):
                np.testing.assert_almost_equal(result_1, result_2)

        # random type initialisation should produce factor matrices each of which is not orthonormal
        rank = (3,)
        cpd = CPD(init='random')
        fmat = cpd._init_fmat(tensor=tensor, rank=rank)
        for mat in fmat:
            result_1 = np.dot(mat.T, mat)
            result_2 = np.eye(rank[0])
            # since each mat is randomly initialized it is not orthonormal
            with pytest.raises(AssertionError):
                np.testing.assert_almost_equal(result_1, result_2)

        # unknown type of initialisation
        with pytest.raises(NotImplementedError):
            rank = (min(tensor.shape)-1,)
            cpd = CPD(init='qwerty')
            cpd._init_fmat(tensor=tensor, rank=rank)

    def test_decompose(self):
        """ Tests for decompose method """
        # ------ tests for termination conditions
        captured_output = io.StringIO()     # Create StringIO object for testing verbosity
        sys.stdout = captured_output        # and redirect stdout.
        np.random.seed(0)
        shape = (6, 7, 8)
        size = reduce(lambda x, y: x * y, shape)
        array_3d = np.random.randn(size).reshape(shape)
        tensor = Tensor(array_3d)
        rank = (2,)
        cpd = CPD(verbose=True)

        # check for termination at max iter
        cpd.max_iter = 10
        cpd.epsilon = 0.01
        cpd.tol = 0.0001
        cpd.decompose(tensor=tensor, rank=rank)
        assert not cpd.converged
        assert len(cpd.cost) == cpd.max_iter
        assert cpd.cost[-1] > cpd.epsilon

        # check for termination when acceptable level of approximation is achieved
        cpd.max_iter = 20
        cpd.epsilon = 0.91492
        cpd.tol = 0.0001
        cpd.decompose(tensor=tensor, rank=rank)
        assert not cpd.converged
        assert len(cpd.cost) < cpd.max_iter
        assert cpd.cost[-1] <= cpd.epsilon

        # check for termination at convergence
        cpd.max_iter = 20
        cpd.epsilon = 0.01
        cpd.tol = 0.0001
        cpd.decompose(tensor=tensor, rank=rank)
        assert cpd.converged
        assert len(cpd.cost) < cpd.max_iter
        assert cpd.cost[-1] > cpd.epsilon

        assert captured_output.getvalue() != ''  # to check that something was actually printed

        # ------ tests for correct output type and values

        shape = (4, 5, 6)
        size = reduce(lambda x, y: x * y, shape)
        array_3d = np.arange(size, dtype='float32').reshape(shape)
        tensor = Tensor(array_3d)
        rank = (7,)

        cpd = CPD(init='random', max_iter=50, epsilon=10e-3, tol=10e-5)

        tensor_cpd = cpd.decompose(tensor=tensor, rank=rank)
        assert isinstance(tensor_cpd, TensorCPD)
        assert tensor_cpd.order == tensor.order
        assert tensor_cpd.rank == rank
        # check dimensionality of computed factor matrices
        for mode, fmat in enumerate(tensor_cpd.fmat):
            assert fmat.shape == (tensor.shape[mode], rank[0])

        tensor_rec = tensor_cpd.reconstruct
        np.testing.assert_almost_equal(tensor_rec.data, tensor.data)

        # ------ tests that should FAIL due to wrong input type
        cpd = CPD()
        # tensor should be Tensor class
        with pytest.raises(TypeError):
            shape = (5, 5, 5)
            size = reduce(lambda x, y: x * y, shape)
            incorrect_tensor = np.arange(size).reshape(shape)
            correct_rank = (2,)
            cpd.decompose(tensor=incorrect_tensor, rank=correct_rank)
        # rank should be a tuple
        with pytest.raises(TypeError):
            shape = (5, 5, 5)
            size = reduce(lambda x, y: x * y, shape)
            correct_tensor = Tensor(np.arange(size).reshape(shape))
            incorrect_rank = [2]
            cpd.decompose(tensor=correct_tensor, rank=incorrect_rank)
        # incorrect length of rank
        with pytest.raises(ValueError):
            shape = (5, 5, 5)
            size = reduce(lambda x, y: x * y, shape)
            correct_tensor = Tensor(np.arange(size).reshape(shape))
            incorrect_rank = (2, 3)
            cpd.decompose(tensor=correct_tensor, rank=incorrect_rank)

    def test_converged(self):
        """ Tests for converged method """
        tol = 0.01
        cpd = CPD(tol=tol)

        # when it is empty, which is the case at the object creation
        assert not cpd.converged

        # requires at least two values
        cpd.cost = [0.001]
        assert not cpd.converged

        # difference greater then `tol`
        cpd.cost = [0.1, 0.2]
        assert not cpd.converged

        # checks only the last two values
        cpd.cost = [0.0001, 0.0002, 0.1, 0.2]
        assert not cpd.converged

        cpd.cost = [0.001, 0.0001]
        assert cpd.converged

        cpd.cost = [0.1, 0.2, 0.001, 0.0001]
        assert cpd.converged

    def test_plot(self):
        """ Tests for plot method """
        # This is only for coverage at the moment
        captured_output = io.StringIO()     # Create StringIO object for testing verbosity
        sys.stdout = captured_output        # and redirect stdout.
        cpd = CPD()
        cpd.plot()
        assert captured_output.getvalue() != ''  # to check that something was actually printed
