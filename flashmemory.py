"""
Cython implementation of FlashPCAngsd (Memory based).
Performs iterative SVD of allele count matrix (EM-PCA) based on custom Halko method.

Jonas Meisner, Siyang Liu and Anders Albrechtsen

Example usage: python flashmemory.py -D matrix.npy -Dt matrix.trans.npy -e 2 -t 64 -o flash
"""

__author__ = "Jonas Meisner"

# Libraries
import shared
import halko
import numpy as np
import argparse
from sklearn.utils.extmath import svd_flip
from scipy import linalg

### Custom SVD functions ###
# Range finder of Q
def range_finder(D, Dt, f, e, F, p, W, s, U, svd_power, t):
	n, m = D.shape
	K = e + 10
	C = np.empty((m, K), dtype=np.float32)

	# Sample Gaussian vectors
	np.random.seed(0)
	Q = np.random.normal(size=(n, K)).astype(np.float32, copy=False)

	# Power iterations
	for pow_i in range(svd_power):
		if (F is None) & (W is None):
			halko.matMulTrans_Freq(Dt, f, Q, C, t)
			C, _ = linalg.lu(C, permute_l=True)
			halko.matMul_Freq(D, f, C, Q, t)
			Q, _ = linalg.lu(Q, permute_l=True)
		elif (W is None):
			halko.matMulTrans_Guide(Dt, f, F, p, Q, C, t)
			C, _ = linalg.lu(C, permute_l=True)
			halko.matMul_Guide(D, f, F, p, C, Q, t)
			Q, _ = linalg.lu(Q, permute_l=True)
		else:
			halko.matMulTrans_SVD(Dt, f, W.T, s, U.T, Q, C, t)
			C, _ = linalg.lu(C, permute_l=True)
			halko.matMul_SVD(D, f, W, s, U, C, Q, t)
			Q, _ = linalg.lu(Q, permute_l=True)
	if (F is None) & (W is None):
		halko.matMulTrans_Freq(Dt, f, Q, C, t)
	elif (W is None):
		halko.matMulTrans_Guide(Dt, f, F, p, Q, C, t)
	else:
		halko.matMulTrans_SVD(Dt, f, W.T, s, U.T, Q, C, t)
	Q, _ = linalg.qr(C, mode='economic')
	return Q

# Range finder of Q when mapping back to domain for E=WSU.T
def range_finder_domain(D, Dt, f, e, W, s, U, svd_power, t):
	n, m = D.shape
	K = e + 10
	C = np.empty((m, K), dtype=np.float32)

	# Sample Gaussian vectors
	np.random.seed(0)
	Q = np.random.normal(size=(n, K)).astype(np.float32, copy=False)

	# Power iterations
	for pow_i in range(svd_power):
		halko.matMulTrans_SVD_domain(Dt, f, W.T, s, U.T, Q, C, t)
		C, _ = linalg.lu(C, permute_l=True)
		halko.matMul_SVD_domain(D, f, W, s, U, C, Q, t)
		Q, _ = linalg.lu(Q, permute_l=True)
	halko.matMulTrans_SVD_domain(Dt, f, W.T, s, U.T, Q, C, t)
	Q, _ = linalg.qr(C, mode='economic')
	return Q

# Range finder of Q for final iteration
def range_finder_final(D, Dt, f, e, F, p, W, s, U, svd_power, t):
	n, m = D.shape
	K = e + 10
	C = np.empty((m, K), dtype=np.float32)

	# Sample Gaussian vectors
	np.random.seed(0)
	Q = np.random.normal(size=(n, K)).astype(np.float32, copy=False)

	# Power iterations
	for pow_i in range(svd_power):
		if (F is None) & (W is None):
			halko.matMulTransFinal_Freq(Dt, f, Q, C, t)
			C, _ = linalg.lu(C, permute_l=True)
			halko.matMulFinal_Freq(D, f, C, Q, t)
			Q, _ = linalg.lu(Q, permute_l=True)
		elif (W is None):
			halko.matMulTransFinal_Guide(Dt, f, F, p, Q, C, t)
			C, _ = linalg.lu(C, permute_l=True)
			halko.matMulFinal_Guide(D, f, F, p, C, Q, t)
			Q, _ = linalg.lu(Q, permute_l=True)
		else:
			halko.matMulTransFinal_SVD(Dt, f, W.T, s, U.T, Q, C, t)
			C, _ = linalg.lu(C, permute_l=True)
			halko.matMulFinal_SVD(D, f, W, s, U, C, Q, t)
			Q, _ = linalg.lu(Q, permute_l=True)
	if (F is None) & (W is None):
		halko.matMulTransFinal_Freq(Dt, f, Q, C, t)
	elif (W is None):
		halko.matMulTransFinal_Guide(Dt, f, F, p, Q, C, t)
	else:
		halko.matMulTransFinal_SVD(Dt, f, W.T, s, U.T, Q, C, t)
	Q, _ = linalg.qr(C, mode='economic')
	return Q

# Acceleration - Range finder of Q
def range_finder_accel(D, Dt, f, e, Ws, U, svd_power, t):
	n, m = D.shape
	K = e + 10
	C = np.empty((m, K), dtype=np.float32)

	# Sample Gaussian vectors
	np.random.seed(0)
	Q = np.random.normal(size=(n, K)).astype(np.float32, copy=False)

	# Power iterations
	for pow_i in range(svd_power):
		halko.matMulTrans_SVD_accel(Dt, f, Ws.T, U.T, Q, C, t)
		C, _ = linalg.lu(C, permute_l=True)
		halko.matMul_SVD_accel(D, f, Ws, U, C, Q, t)
		Q, _ = linalg.lu(Q, permute_l=True)
	halko.matMulTrans_SVD_accel(Dt, f, Ws.T, U.T, Q, C, t)
	Q, _ = linalg.qr(C, mode='economic')
	return Q

# Acceleration - Range finder of Q when mapping back to domain for E=WSU.T
def range_finder_domain_accel(D, Dt, f, e, Ws, U, svd_power, t):
	n, m = D.shape
	K = e + 10
	C = np.empty((m, K), dtype=np.float32)

	# Sample Gaussian vectors
	np.random.seed(0)
	Q = np.random.normal(size=(n, K)).astype(np.float32, copy=False)

	# Power iterations
	for pow_i in range(svd_power):
		halko.matMulTrans_SVD_domain_accel(Dt, f, Ws.T, U.T, Q, C, t)
		C, _ = linalg.lu(C, permute_l=True)
		halko.matMul_SVD_domain_accel(D, f, Ws, U, C, Q, t)
		Q, _ = linalg.lu(Q, permute_l=True)
	halko.matMulTrans_SVD_domain_accel(Dt, f, Ws.T, U.T, Q, C, t)
	Q, _ = linalg.qr(C, mode='economic')
	return Q

# Iterative SVD
def customSVD(D, Dt, f, e, F, p, W, s, U, svd_power, t):
	n, m = D.shape
	Q = range_finder(D, Dt, f, e, F, p, W, s, U, svd_power, t)
	Bt = np.zeros((n, Q.shape[1]), dtype=np.float32)

	# B.T = dot(E.T, Q)
	if (F is None) & (W is None):
		halko.matMul_Freq(D, f, Q, Bt, t)
	elif (W is None):
		halko.matMul_Guide(D, f, F, p, Q, Bt, t)
	else:
		halko.matMul_SVD(D, f, W, s, U, Q, Bt, t)

	# SVD on thin matrix
	Uhat, s, V = linalg.svd(Bt.T, full_matrices=False)
	del Bt
	U = np.dot(Q, Uhat)

	# Correct sign
	U, V = svd_flip(U, V, u_based_decision=False)
	return V[:e,:].T, s[:e], U[:,:e].T

# Map to domain SVD
def customDomainSVD(D, Dt, f, e, W, s, U, svd_power, t):
	n, m = D.shape
	Q = range_finder_domain(D, Dt, f, e, W, s, U, svd_power, t)
	Bt = np.zeros((n, Q.shape[1]), dtype=np.float32)

	# B.T = dot(E.T, Q)
	halko.matMul_SVD_domain(D, f, W, s, U, Q, Bt, t)

	# SVD on thin matrix
	Uhat, s, V = linalg.svd(Bt.T, full_matrices=False)
	del Bt
	U = np.dot(Q, Uhat)

	# Correct sign
	U, V = svd_flip(U, V, u_based_decision=False)
	return V[:e,:].T, s[:e], U[:,:e].T

# Final SVD
def customFinalSVD(D, Dt, f, e, F, p, W, s, U, svd_power, t):
	n, m = D.shape
	Q = range_finder_final(D, Dt, f, e, F, p, W, s, U, svd_power, t)
	Bt = np.zeros((n, Q.shape[1]), dtype=np.float32)

	# B.T = dot(E.T, Q)
	if (F is None) & (W is None):
		halko.matMulFinal_Freq(D, f, Q, Bt, t)
	elif (W is None):
		halko.matMulFinal_Guide(D, f, F, p, Q, Bt, t)
	else:
		halko.matMulFinal_SVD(D, f, W, s, U, Q, Bt, t)

	# SVD on thin matrix
	Uhat, s, V = linalg.svd(Bt.T, full_matrices=False)
	del Bt
	U = np.dot(Q, Uhat)

	# Correct sign
	U, V = svd_flip(U, V, u_based_decision=False)
	return V[:e,:].T, s[:e], U[:,:e].T

# Acceleration - Iterative SVD
def customSVD_accel(D, Dt, f, e, Ws, U, svd_power, t):
	n, m = D.shape
	Q = range_finder_accel(D, Dt, f, e, Ws, U, svd_power, t)
	Bt = np.zeros((n, Q.shape[1]), dtype=np.float32)

	# B.T = dot(E.T, Q)
	halko.matMul_SVD_accel(D, f, Ws, U, Q, Bt, t)

	# SVD on thin matrix
	Uhat, s, V = linalg.svd(Bt.T, full_matrices=False)
	del Bt
	U = np.dot(Q, Uhat)

	# Correct sign
	U, V = svd_flip(U, V, u_based_decision=False)
	return V[:e,:].T, s[:e], U[:,:e].T

# Acceleration - Map to domain SVD
def customDomainSVD_accel(D, Dt, f, e, Ws, U, svd_power, t):
	n, m = D.shape
	Q = range_finder_domain_accel(D, Dt, f, e, Ws, U, svd_power, t)
	Bt = np.zeros((n, Q.shape[1]), dtype=np.float32)

	# B.T = dot(E.T, Q)
	halko.matMul_SVD_domain_accel(D, f, Ws, U, Q, Bt, t)

	# SVD on thin matrix
	Uhat, s, V = linalg.svd(Bt.T, full_matrices=False)
	del Bt
	U = np.dot(Q, Uhat)

	# Correct sign
	U, V = svd_flip(U, V, u_based_decision=False)
	return V[:e,:].T, s[:e], U[:,:e].T


### Main function ###
def flashMemory(D, Dt, f, e, K, M, M_tole, F, p, W, s, U, svd_power, indf_save, output, accel, t):
	n, m = D.shape # Dimensions

	if accel:
		print("Using accelerated EM scheme (SqS3)")
		diffW_1 = np.empty((n, e), dtype=np.float32)
		diffW_2 = np.empty((n, e), dtype=np.float32)
		diffW_3 = np.empty((n, e), dtype=np.float32)
		diffU_1 = np.empty((e, m), dtype=np.float32)
		diffU_2 = np.empty((e, m), dtype=np.float32)
		diffU_3 = np.empty((e, m), dtype=np.float32)

	if M < 1:
		print("Warning, no EM-PCA iterations are performed!")
		print("Inferring set of eigenvector(s).")
		V, s, U = customFinalSVD(D, Dt, f, e, F, p, W, s, U, svd_power, t)
		return V, s, U
	else:
		# Estimate initial individual allele frequencies
		if accel:
			print("Initiating accelerated EM scheme (1)")
		if (W is None):
			W, s, U = customSVD(D, Dt, f, e, F, p, W, s, U, svd_power, t)
		else:
			W, s, U = customDomainSVD(D, Dt, f, e, W, s, U, svd_power, t)
		if not accel:
			print("Individual allele frequencies estimated (1).")
		else:
			W = W*s
		prevU = np.copy(U)

		# Iterative estimation of individual allele frequencies
		for iteration in range(2, M+1):
			if accel:
				if iteration > 2:
					W1, s1, U1 = customDomainSVD_accel(D, Dt, f, e, W, U, svd_power, t)
				else:
					W1, s1, U1 = customSVD_accel(D, Dt, f, e, W, U, svd_power, t)
				W1 = W1*s1
				shared.matMinus(W1, W, diffW_1)
				shared.matMinus(U1, U, diffU_1)
				sr2_W = shared.matSumSquare(diffW_1)
				sr2_U = shared.matSumSquare(diffU_1)
				W2, s2, U2 = customSVD_accel(D, Dt, f, e, W1, U1, svd_power, t)
				W2 = W2*s2
				shared.matMinus(W2, W1, diffW_2)
				shared.matMinus(U2, U1, diffU_2)

				# SQUAREM update of W and U SqS3
				shared.matMinus(diffW_2, diffW_1, diffW_3)
				shared.matMinus(diffU_2, diffU_1, diffU_3)
				sv2_W = shared.matSumSquare(diffW_3)
				sv2_U = shared.matSumSquare(diffU_3)
				alpha_W = np.sqrt(sr2_W/sv2_W)
				alpha_U = np.sqrt(sr2_U/sv2_U)

				# New accelerated update
				shared.matUpdate(W, diffW_1, diffW_3, alpha_W)
				shared.matUpdate(U, diffU_1, diffU_3, alpha_U)
			else:
				W, s, U = customDomainSVD(D, Dt, f, e, W, s, U, svd_power, t)

			# Break iterative update if converged
			diff = np.sqrt(np.sum(shared.rmse(U.T, prevU.T, t))/(m*e))
			print("Individual allele frequencies estimated (" + str(iteration) + "). RMSE=" + str(diff))
			if diff < M_tole:
				print("Estimation of individual allele frequencies has converged.")
				break
			prevU = np.copy(U)
		del prevU

		if accel:
			W, s, U = customDomainSVD_accel(D, Dt, f, e, W, U, svd_power, t)
			del W1, W2, s1, s2, U1, U2, diffW_1, diffW_2, diffW_3, diffU_1, diffU_2, diffU_3

		if indf_save:
			print("Saving singular matrices for future use (.w.npy, .s.npy, .u.npy).")
			np.save(output + ".w", W)
			np.save(output + ".s", s)
			np.save(output + ".u", U)

		# Estimating SVD
		print("Inferring set of eigenvector(s).")
		V, s, U = customFinalSVD(D, Dt, f, e, F, p, W, s, U, svd_power, t)
		del W
		
		return V, s, U


##### Argparse #####
parser = argparse.ArgumentParser(prog="FlashPCAngsd Memory")
parser.add_argument("--version", action="version", version="%(prog)s alpha 0.45")
parser.add_argument("-D", metavar="FILE",
	help="Input file (.npy)")
parser.add_argument("-Dt", metavar="FILE",
	help="Input file (transposed) (.npy)")
parser.add_argument("-e", metavar="INT", type=int,
	help="Number of eigenvectors to use in IAF estimation")
parser.add_argument("-k", metavar="INT", type=int,
	help="Number of eigenvectors to output in final SVD")
parser.add_argument("-m", metavar="INT", type=int, default=100,
	help="Maximum iterations for estimation of individual allele frequencies (100)")
parser.add_argument("-m_tole", metavar="FLOAT", type=float, default=1e-6,
	help="Tolerance for update in estimation of individual allele frequencies (1e-6)")
parser.add_argument("-t", metavar="INT", type=int, default=1,
	help="Number of threads")
parser.add_argument("-maf", metavar="FLOAT", type=float, default=0.00,
	help="Threshold for minor allele frequencies (0.00)")
parser.add_argument("-selection", action="store_true",
	help="Perform PC-based selection scan (Galinsky et al. 2016)")
parser.add_argument("-maf_save", action="store_true",
	help="Save estimated population allele frequencies")
parser.add_argument("-bool_save", action="store_true",
	help="Save boolean vector used in MAF filtering (Binary)")
parser.add_argument("-indf_save", action="store_true",
	help="Save estimated singular matrices")
parser.add_argument("-index", metavar="FILE",
	help="Index for guided allele frequencies")
parser.add_argument("-svd", metavar="STRING", default="arpack",
	help="Method for performing truncated SVD (ARPACK/Randomized)")
parser.add_argument("-svd_power", metavar="INT", type=int, default=4,
	help="Number of power iterations in randomized SVD")
parser.add_argument("-w", metavar="FILE",
	help="Left singular matrix (.w.npy)")
parser.add_argument("-s", metavar="FILE",
	help="Singular values (.s.npy)")
parser.add_argument("-u", metavar="FILE",
	help="Right singular matrix (.u.npy)")
parser.add_argument("-accel", action="store_true",
	help="Accelerated EM")
parser.add_argument("-o", metavar="OUTPUT", help="Prefix output file name", default="flash")
args = parser.parse_args()


### Caller ####
print("FlashPCAngsd Memory 0.45\n")
assert args.Dt is not None, "Memory efficient method must be provided transposed C-contiguous data matrix!"

# Set K
if args.k is None:
	K = args.e
else:
	K = args.k

# Read in single-read matrix
print("Reading in single-read sampling matrices from binary NumPy files.")
# Read from binary NumPy file. Expects np.int8 data format
D = np.load(args.D)
Dt = np.load(args.Dt)
assert D.dtype == np.int8, "NumPy array must be of 8-bit integer format (np.int8)!"
assert Dt.dtype == np.int8, "NumPy array must be of 8-bit integer format (np.int8)!"
n, m = D.shape

# Population allele frequencies
print("Estimating population allele frequencies.")
f = np.empty(m, dtype=np.float32)
shared.estimateF(D, f, args.t)

# Removing rare variants
if args.maf > 0.0:
	mask = (f >= args.maf) & (f <= (1 - args.maf))
	print("Filtering variants with a MAF filter of " + str(args.maf) + ".")
	f = np.compress(mask, f)
	D = np.compress(mask, D, axis=1)
	Dt = np.compress(mask, Dt, axis=0)

n, m = D.shape
print(str(n) + " samples, " + str(m) + " sites.\n")

# Guided meta allele frequencies
if (args.index is not None) & (args.w is None):
	print("Estimating guided allele frequencies.")
	p = np.load(args.index)
	F = np.zeros((m, max(p)+1), dtype=np.float32)
	shared.estimateF_guided(D, f, F, p, args.t)
else:
	p, F = None, None

# Use eigenvectors from previous run
if args.w is not None:
	assert args.s is not None, "Must supply both -s and -u along with -w!"
	assert args.u is not None, "Must supply both -s and -u along with -w!"
	print("Reading singular matrices from previous run.")
	W = np.load(args.w)
	assert W.shape[0] == n, "Number of samples in W must match D!"
	s = np.load(args.s)
	U = np.load(args.u)
	assert U.shape[1] == m, "Number of sites in U must match D!"
else:
	W, s, U = None, None, None

# FlashPCAngsd
print("Performing FlashPCAngsd Memory.")
print("Using " + str(args.e) + " eigenvector(s).")
V, s, U = flashMemory(D, Dt, f, args.e, K, args.m, args.m_tole, F, p, W, s, U, args.svd_power, \
	args.indf_save, args.o, args.accel, args.t)

print("Saving eigenvector(s) as " + args.o + ".eigenvecs.npy (Binary).")
np.save(args.o + ".eigenvecs", V.astype(float, copy=False))
print("Saving eigenvalue(s) as " + args.o + ".eigenvals (Text).")
np.savetxt(args.o + ".eigenvals", s**2/m)

if args.selection:
	print("Performing selection scan along each PC.")
	Dsquared = np.zeros((m, args.e), dtype=np.float32)
	shared.galinskyScan(U[:args.e], Dsquared, args.t)
	print("Saving test statistics as " + args.o + ".selection.npy (Binary).")
	np.save(args.o + ".selection", Dsquared.astype(float, copy=False))
	del Dsquared # Clear memory
del U # Clear memory

if args.maf_save:
	print("Saving population allele frequencies as " + args.o + ".maf.npy (Binary).")
	np.save(args.o + ".maf", f.astype(float, copy=False))
del f # Clear memory

if (args.bool_save) and (args.maf > 0.0):
	print("Saving boolean vector for used in MAF filtering as " + args.o + ".bool.npy (Binary)")
	np.save(args.o + ".bool", mask.astype(int, copy=False))