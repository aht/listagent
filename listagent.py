# Copyright (c) 2009 Anh Hai Trinh
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
A listagent can access and mutate a slice of an original list "live": it never
creates any copy of the original and only refers to it via "address translation".
It is faster than a normal slice if you only need a few elements out of a
slice.

Listagents offer live view of the original::

  >>> x = [0, 1, 2, 3, 4, 5, 6, 7]
  >>> a = listagent(x)[1:-1:2]
  >>> list(a)
  [1, 3, 5]
  >>> x += [8, 9, 10]
  >>> a.align()
  >>> list(a)
  [1, 3, 5, 7, 9]

Slice assignment also works::

  >>> x = [0, 1, 2, 3, 4, 5, 6, 7]
  >>> a = listagent(x)[::2]
  >>> a[:] = listagent(x)[::-2]
  >>> x
  [7, 1, 5, 3, 3, 5, 1, 7]

You can sort and reverse the agent, which will mutate the original list
in-place.  The sort algorithm is Shell sort::

  >>> x = [22, 7, 2, -5, 8, 4]
  >>> a = listagent(x)

  >>> a[1:].sort()
  >>> x
  [22, -5, 2, 4, 7, 8]

  >>> a[::2].reverse()
  >>> x
  [7, -5, 2, 4, 22, 8]

Some test cases::

  >>> list(a[1::2])
  [-5, 4, 8]

  >>> list(a[1:-1])
  [-5, 2, 4, 22]

  >>> list(a[::-1])
  [8, 22, 4, 2, -5, 7]
"""

import collections


class listagent(collections.MutableSequence):
	def __init__(self, list, slice=slice(None)):
		self.list = list
		self.slice = slice
		self.align()

	def align(self):
		"""Align the agent to the length of the underlying list"""
		start, stop, step = self.slice.indices(len(self.list))
		self.translate = lambda i: start + i * step
		if step > 0:
			self.len = int((stop - start - 1) / float(step)) + 1
		else:
			self.len = int((stop - start) / float(step))

	def __len__(self):
		return self.len

	def __iter__(self):
		def iterate():
			x = self.list
			t = self.translate
			for i in range(len(self)):
				yield x[t(i)]
		return iterate()

	def __getitem__(self, key):
		if type(key) is slice:
			if key == slice(None):
				## what's the point?
				return self
			elif self.slice == slice(None):
				return listagent(self.list, key)
			else:
				return listagent(self, key)
		elif type(key) is int:
			return self.list[self.translate(key)]
		else:
			raise TypeError

	def __setitem__(self, key, value):
		if type(key) is int:
			self.list[self.translate(key)] = value
		elif type(key) is slice:
			x = self.list
			t = self.translate
			for i in range(len(self)):
				try:
					x[t(i)] = value[i]
				except IndexError:
					raise ValueError("length mismatch")
		else:
			raise TypeError
	
	def __delitem__(self, key):
		if type(key) is int:
			del self.list[self.translate(key)]
		elif type(key) is slice:
			raise NotImplementedError
		raise TypeError
	
	def insert(self, i, value):
		self.list.insert(self.translate(i), value)
		self.align()

	def reverse(self):
		x = self.list
		t = self.translate
		i, j = 0, len(self)-1
		while i <= j:
			x[t(i)], x[t(j)] = x[t(j)], x[t(i)]
			i += 1
			j -= 1

	def sort(self):
		## Shell sort ##
		x = self.list
		n = len(self)
		t = map(self.translate, range(n))
		gap = n // 2
		while gap:
			for k in range(n):
				i, j = t[k], t[k-gap]
				tmp = x[i]
				while k >= gap and x[j] > tmp:
					x[i] = x[j]
					k -= gap
					i, j = t[k], t[k-gap]
				x[i] = tmp
			gap = 1 if gap == 2 else int(gap * 5.0 / 11)

	def __repr__(self):
		s = ':'.join(map(str, [self.slice.start, self.slice.stop, self.slice.step]))
		s = s.replace('None', '')
		return "<listagent[%s] of 0x%x>" % (s, id(self.list))


def permute_next(a):
	"""Transform the given mutable sequence into its next lexicographical
	permutation.  Return True if that permutation exists, else False.

	>>> x = [4, 5, 3, 2 ,1]
	>>> permute_next(x)
	True
	>>> x
	[5, 1, 2, 3, 4]
	
	>>> y = [3, 3, 4, 2, 1]
	>>> permute_next(y)
	True
	>>> y
	[3, 4, 1, 2, 3]
	
	>>> permute_next([5, 4, 2, 0])
	False
	"""
	i = len(a) - 2
	while i >= 0 and a[i+1] <= a[i]:
		i -= 1
	if i < 0:
		# a is monotonically decreasing
		return False
	else:
		# a[i+1:] is monotonically decreasing
		j = len(a) - 1
		while a[j] <= a[i]:
			j -= 1
		a[i], a[j] = a[j], a[i]
		listagent(a)[i+1:].reverse()
		return True
