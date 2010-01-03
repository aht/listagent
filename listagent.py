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

  $ python -m timeit "range(1000000)[1:-1:5][::7][10000:-10000:42]"
  10 loops, best of 3: 280 msec per loop

  $ python -m timeit -s "from listagent import listagent" \
    "list(listagent(range(1000000))[1:-1:5][::7][10000:-10000:42])"
  10 loops, best of 3: 54 msec per loop

Listagents offer live view of the original::

  >>> x = [0, 1, 2, 3, 4, 5, 6, 7]
  >>> a = sliceagent(x)[1:-1:2]
  >>> list(a)
  [1, 3, 5]
  >>> x[5] = -1
  >>> a[2]
  -1

When the length of the underlying list changes, an agent must be re-aligned::

  >>> x += [8, 9, 10]
  >>> a.align()
  >>> list(a)
  [1, 3, -1, 7, 9]

But this is not necessary if the change is brought about by the agent itself::

  >>> del a[2]
  >>> list(a)
  >>> [1, 3, 7, 9]

By now, the agent has mutated the original list::

  >>> x
  [0, 1, 2, 3, 4, 6, 7, 8, 9, 10]

Slice assignment also works::

  >>> x = [0, 1, 2, 3, 4, 5, 6, 7]
  >>> a = sliceagent(x)[::2]
  >>> a[:] = sliceagent(x)[::-2]
  >>> x
  [7, 1, 5, 3, 3, 5, 1, 7]

You can also sort and reverse the agent, the sort algorithm is Shell sort::

  >>> x = [22, 7, 2, -5, 8, 4]
  >>> a = sliceagent(x)

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


class sliceagent(collections.MutableSequence):
	def __init__(self, list, slice=slice(None)):
		self.list = list
		self.slice = slice
		self.align()

	def align(self):
		"""Align the agent to the length of the underlying list"""
		start, stop, step = self.slice.indices(len(self.list))
		if step > 0:
			n = int((stop - start - 1) / float(step)) + 1
		else:
			n = int((stop - start) / float(step))
		self.n = n
		self.translate = lambda i: start + i * step

	def __len__(self):
		return self.n

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
				return sliceagent(self.list, key)
			else:
				## TODO: it should be possible to compose slices
				## without relying on multiple agents
				return sliceagent(self, key)
		elif type(key) is int:
			n = len(self)
			if key >= n:
				raise IndexError
			elif key < 0:
				if key < -n:
					raise IndexError
				key = key % n
			return self.list[self.translate(key)]
		else:
			raise TypeError

	def __setitem__(self, key, value):
		if type(key) is int:
			self.list[self.translate(key)] = value
		elif type(key) is slice:
			x = self.list
			t = self.translate
			v = iter(value)
			for i in range(len(self)):
				try:
					x[t(i)] = next(v)
				except StopIteration:
					raise ValueError("length mismatch")
		else:
			raise TypeError
	
	def __delitem__(self, key):
		if type(key) is int:
			del self.list[self.translate(key)]
			self.align()
		elif type(key) is slice:
			raise NotImplementedError
		else:
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


def next_permutation(a):
	"""Transform the given mutable sequence into its succeeding lexicographical
	permutation.  Return True if that permutation exists, else False.

	>>> x = [4, 5, 3, 2 ,1]
	>>> next_permutation(x)
	True
	>>> x
	[5, 1, 2, 3, 4]
	
	>>> y = [3, 3, 4, 2, 1]
	>>> next_permutation(y)
	True
	>>> y
	[3, 4, 1, 2, 3]
	
	>>> next_permutation([5, 4, 2, 0])
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
		sliceagent(a)[i+1:].reverse()
		return True
