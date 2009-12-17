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
  >>> list(a)
  [1, 3, 5, 7, 9]

Slice assignment also works::

  >>> x = [0, 1, 2, 3, 4, 5, 6, 7]
  >>> a = listagent(x)[::2]
  >>> a[:] = listagent(x)[::-2]
  >>> x
  [7, 1, 5, 3, 3, 5, 1, 7]

You can sort and reverse the agent, which will mutate the original list
in-place.  Reversing is as fast as list.reverse.  The sort algorithm is Shell
sort and is slower than list.sort (which is timsort)::

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


def idx_translator(start, stop, step):
	return lambda i: start + i * step


class listagent(collections.MutableSequence):
	def __init__(self, list, slice=slice(None)):
		self.list = list
		self.slice = slice

	def __len__(self):
		start, stop, step = self.slice.indices(len(self.list))
		if step > 0:
			return int((stop - start - 1) / float(step)) + 1
		else:
			return int((stop - start) / float(step))

	def __iter__(self):
		t = idx_translator(*self.slice.indices(len(self.list)))
		def iterate():
			for i in range(len(self)):
				yield self.list[t(i)]
		return iterate()

	def __getitem__(self, key):
		if type(key) is type(slice(1)):
			if key == slice(None):
				## what's the point?
				return self
			elif self.slice == slice(None):
				return listagent(self.list, key)
			else:
				return listagent(self, key)
		elif type(key) is type(1):
			t = idx_translator(*self.slice.indices(len(self.list)))
			return self.list[t(key)]
		else:
			raise TypeError

	def __setitem__(self, key, value):
		t = idx_translator(*self.slice.indices(len(self.list)))
		if type(key) is type(1):
			self.list[t(key)] = value
		elif type(key) is type(slice(1)):
			v = iter(value)
			for i in range(len(self)):
				try:
					self.list[t(i)] = next(v)
				except StopIteration:
					raise ValueError("length mismatch")
		else:
			raise TypeError
	
	def __delitem__(self, key):
		if type(key) is type(1):
			t = idx_translator(*self.slice.indices(len(self.list)))
			del self.list[t(key)]
	
	def insert(self, i, value):
		t = idx_translator(*self.slice.indices(len(self.list)))
		self.list.insert(t(i), value)

	def reverse(self):
		t = idx_translator(*self.slice.indices(len(self.list)))
		n = len(self)
		for k in range(n // 2):
			i, j = t(k), t((-k-1) % n)
			self.list[i], self.list[j] = self.list[j], self.list[i]

	def sort(self):
		## Shell sort ##
		n = len(self)
		translator = idx_translator(*self.slice.indices(len(self.list)))
		t = map(translator, range(n))
		gap = n // 2
		while gap:
			for k in range(n):
				i, j = t[k], t[k-gap]
				tmp = self.list[i]
				while k >= gap and self.list[j] > tmp:
					self.list[i] = self.list[j]
					k -= gap
					i, j = t[k], t[k-gap]
				self.list[i] = tmp
			gap = 1 if gap == 2 else int(gap * 5.0 / 11)

	def __repr__(self):
		s = ':'.join(map(str, [self.slice.start, self.slice.stop, self.slice.step]))
		s = s.replace('None', '')
		return "<listagent[%s] of 0x%x>" % (s, id(self.list))

if __name__ == '__main__':
	pass
