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
  [1, 3, 6, 8]

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
	def __init__(self, sequence, slice=slice(None)):
		self.origin = sequence
		self.slice = slice
		self.align()

	def align(self):
		"""Align the agent to the length of the underlying list"""
		start, stop, step = self.slice.indices(len(self.origin))
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
			x = self.origin
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
				return sliceagent(self.origin, key)
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
			return self.origin[self.translate(key)]
		else:
			raise TypeError

	def __setitem__(self, key, value):
		if type(key) is int:
			self.origin[self.translate(key)] = value
		elif type(key) is slice:
			x = self.origin
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
			del self.origin[self.translate(key)]
			self.align()
		elif type(key) is slice:
			raise NotImplementedError
		else:
			raise TypeError
	
	def insert(self, i, value):
		self.origin.insert(self.translate(i), value)
		self.align()

	def reverse(self):
		x = self.origin
		t = self.translate
		i, j = 0, len(self)-1
		while i <= j:
			x[t(i)], x[t(j)] = x[t(j)], x[t(i)]
			i += 1
			j -= 1

	def sort(self):
		## Shell sort ##
		x = self.origin
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
		return "<listagent[%s] of 0x%x>" % (s, id(self.origin))


class chainagent(collections.MutableSequence):
	def __init__(self, *sequences):
		self.origin = sequences
	
	def align(self):
		self.n = map(len, sequences)



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


def partial_sort(x, y):
	"""Transform the the congregration of the two given mutable sequence,
	such that the smallest elements are sorted into the first sequence.

	>>> x = [74,97,22,35,99,27,17,87,82,100,97,87,94,37,16,4,12,58,4,78]
	>>> a = sliceagent(x)

	### Move the 5 smallest elements with even indices up the list
	>>> partial_sort(a[:10:2], a[10::2])
	>>> x[:10:2]
	[4, 12, 16, 17, 22]
	"""
	heapify(y)
	for i in range(len(x)):
		if x[i] > y[0]:
			x[i] = heappushpop(y, x[i])
	x.sort()


# try:
#   from python import heapq [sic!]
# except that:
#   the C implementation does not heapify other mutable sequence types
#   such as deque and agents
# finally:
#   manually copy and paste the code from /usr/lib/python2.6/heapq.py

def heappushpop(heap, item):
	"""Fast version of a heappush followed by a heappop."""
	if heap and heap[0] < item:
		item, heap[0] = heap[0], item
		_siftup(heap, 0)
	return item

def heapify(x):
	"""Transform list into a heap, in-place, in O(len(heap)) time."""
	n = len(x)
	for i in reversed(xrange(n//2)):
		_siftup(x, i)

def _siftdown(heap, startpos, pos):
	newitem = heap[pos]
	# Follow the path to the root, moving parents down until finding a place
	# newitem fits.
	while pos > startpos:
		parentpos = (pos - 1) >> 1
		parent = heap[parentpos]
		if newitem < parent:
			heap[pos] = parent
			pos = parentpos
			continue
		break
	heap[pos] = newitem

def _siftup(heap, pos):
	endpos = len(heap)
	startpos = pos
	newitem = heap[pos]
	# Bubble up the smaller child until hitting a leaf.
	childpos = 2*pos + 1	# leftmost child position
	while childpos < endpos:
		# Set childpos to index of smaller child.
		rightpos = childpos + 1
		if rightpos < endpos and not heap[childpos] < heap[rightpos]:
			childpos = rightpos
		# Move the smaller child up.
		heap[pos] = heap[childpos]
		pos = childpos
		childpos = 2*pos + 1
	# The leaf at pos is empty now.  Put newitem there, and bubble it up
	# to its final resting place (by sifting its parents down).
	heap[pos] = newitem
	_siftdown(heap, startpos, pos)
