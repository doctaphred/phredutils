from functools import partial, partialmethod
from operator import attrgetter


comparisons = (
    '__lt__',
    '__le__',
    '__eq__',
    '__ne__',
    '__gt__',
    '__ge__',
    )


class Constraint:
    """
    >>> from operator import *
    >>> c = Constraint(eq, 2)
    >>> c
    eq(value, 2)
    >>> c(2)
    True
    >>> c(3)
    False
    >>> c('spam')
    False

    >>> c = Constraint(le, 2)
    >>> c
    le(value, 2)
    >>> c(2)
    True
    >>> c(3)
    False
    >>> c('spam')
    False
    """

    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self, value):
        try:
            result = self.func(value, *self.args, **self.kwargs)
        except Exception:
            # TODO: catch this here, or in Pattern?
            return False

        if result is NotImplemented:
            return False
        return result

    def __repr__(self):
        try:
            func_name = self.func.__name__
        except AttributeError:
            func_name = self.func

        args_strs = [str(arg) for arg in self.args]
        kwargs_strs = ['{}={}'.format(k, v) for k, v in self.kwargs.items()]
        args_str = ', '.join(args_strs + kwargs_strs)

        if args_str:
            return '{}(value, {})'.format(func_name, args_str)
        else:
            return '{}(value)'.format(func_name)


class Pattern:
    """
    >>> anything = Pattern.anything()
    >>> anything
    Pattern({})
    >>> 2 in anything
    True

    >>> p = anything.to(int)
    >>> 3 in p
    True
    >>> 's' in p
    False

    >>> p = anything == 2
    >>> p
    Pattern({__eq__(value, 2)})

    >>> 2 in p
    True
    >>> 2.0 in p
    True
    >>> 2.1 in p
    False

    Chained comparisons use `and` under the hood, so don't use them:

    >>> p = 2 < anything < 4
    >>> p
    Pattern({__lt__(value, 4)})

    If needed, add parentheses, or use |:

    >>> p = (2 < anything) < 4
    >>> p
    Pattern({__gt__(value, 2), __lt__(value, 4)})
    >>> 3 in p
    True

    >>> p = (2 < anything) | (anything < 4)
    >>> p
    Pattern({__gt__(value, 2), __lt__(value, 4)})
    >>> [x in p for x in range(5)]
    [False, False, False, True, False]
    >>> '3' in p
    False
    """

    def __init__(self, constraints):
        self.constraints = constraints

    @classmethod
    def anything(cls):
        return cls(frozenset())

    # TODO: does this work with overridden __eq__?
    # (Answer: no; TODO: what to do instead?)
    # def __hash__(self):
    #     return hash(self.constraints)

    def __add__(self, new_constraint):
        return self.__class__(self.constraints | {new_constraint})

    def __or__(self, other):
        return self.__class__(self.constraints | other.constraints)

    def __and__(self, other):
        return self.__class__(self.constraints & other.constraints)

    def __xor__(self, other):
        return self.__class__(self.constraints ^ other.constraints)

    def __sub__(self, other):
        return self.__class__(self.constraints - other.constraints)

    def __repr__(self):
        constraint_expressions = sorted(str(c) for c in self.constraints)
        return 'Pattern({{{}}})'.format(', '.join(constraint_expressions))

    def to(self, func, *args, **kwargs):
        return self + Constraint(partial(func, *args, **kwargs))

    def matches(self, value, fold=all):
        return fold(constraint(value) for constraint in self.constraints)

    def __contains__(self, value):
        return self.matches(value)

    def delegate(self, name, value):
        # TODO: switch to this, remove .__name__ from Constraint.__repr__:
        # return self + Constraint(methodcaller(name, value))

        getter = attrgetter(name)

        def func(self, *args, **kwargs):
            return getter(self)(*args, **kwargs)
        func.__name__ = name

        return self + Constraint(func, value)

    for name in comparisons:
        locals()[name] = partialmethod(delegate, name)
        del name

    def __getitem__(self, name):
        pass

    isinstance = partialmethod(delegate, isinstance)
    issubclass = partialmethod(delegate, issubclass)
