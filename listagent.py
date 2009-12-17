"""
A listagent can access and mutate a slice of an original list "live": it never
creates any copy of the original and only refers to it via "address
translation".

It is faster if you only need a few elements out of a slice.

>>> x = [22, 7, 2, -5, 8, 4]
>>> a = listagent(x)

>>> a[1:].sort()
>>> x
[22, -5, 2, 4, 7, 8]

>>> a[::2].reverse()
>>> x
[7, -5, 2, 4, 22, 8]

>>> list(a[1:-1])
[-5, 2, 4, 22]

>>> list(a[::-1])
[8, 22, 4, 2, -5, 7]
"""

import collections


def idx_translator(start, stop, step):
	def translator(i):
		i = start + i * step
		if (step > 0 and i >= stop) or (step < 0 and i < 0):
			raise IndexError
		return i
	return translator


class listagent(collections.MutableSequence):
	def __init__(self, list, slice=slice(None)):
		self.list = list
		self.slice = slice

	def __len__(self):
		start, stop, step = self.slice.indices(len(self.list))
		return int((stop - start) / float(step))

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
		if type(key) is type(1):
			t = idx_translator(*self.slice.indices(len(self.list)))
			self.list[t(key)] = value
		elif type(key) is type(slice(1)):
			raise NotImplementedError
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

