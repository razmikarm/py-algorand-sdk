import json

from Cryptodome.Hash import SHA512

from algosdk.abi.tuple_type import TupleType
from algosdk.abi.util import type_from_string
from algosdk import error
from algosdk import constants


# Globals
TRANSACTION_ARGS = (
    constants.PAYMENT_TXN,
    constants.KEYREG_TXN,
    constants.ASSETCONFIG_TXN,
    constants.ASSETTRANSFER_TXN,
    constants.ASSETFREEZE_TXN,
    constants.APPCALL_TXN,
)


class Method:
    """
    Represents a ABI method description.

    Args:
        name (string): name of the method
        args (list): list of Argument objects with type, name, and optional
        description
        returns (Returns): a Returns object with a type and optional description
        desc (string, optional): optional description of the method
    """

    def __init__(self, name, args, returns, desc=None) -> None:
        self.name = name
        self.args = args
        self.desc = desc
        self.returns = (
            returns if (returns and returns.type != "void") else None
        )
        # Calculate number of method calls passed in as arguments and
        # add one for this method call itself.
        txn_count = 1
        for arg in self.args:
            if arg.type in TRANSACTION_ARGS:
                txn_count += 1
        self.txn_calls = txn_count

    def get_signature(self):
        arg_string = ",".join([str(arg.type) for arg in self.args])
        ret_string = self.returns.type if self.returns else "void"
        return "{}({}){}".format(self.name, arg_string, ret_string)

    def get_selector(self):
        """
        Returns the ABI method signature, which is the first four bytes of the
        SHA-512/256 hash of the method signature.

        Returns:
            bytes: first four bytes of the method signature hash
        """
        hash = SHA512.new(truncate="256")
        hash.update((self.get_signature()).encode("utf-8"))
        return hash.digest()[:4]

    def get_txn_calls(self):
        """
        Returns the number of transactions needed to invoke this ABI method.
        """
        return self.txn_calls

    @staticmethod
    def from_json(resp):
        method_dict = json.loads(resp)
        return Method.undictify(method_dict)

    @staticmethod
    def from_string(s):
        # Split string into tokens around outer parentheses.
        # The first token should always be the name of the method,
        # the second token should be the arguments as a tuple,
        # and the last token should be the return type (or void).
        tokens = Method._parse_string(s)
        argument_list = [Argument(t) for t in TupleType.parse_tuple(tokens[1])]
        return_type = Returns(tokens[-1])
        return Method(name=tokens[0], args=argument_list, returns=return_type)

    @staticmethod
    def undictify(d):
        name = d["name"]
        arg_list = [Argument.undictify(arg) for arg in d["args"]]
        return_obj = (
            Returns.undictify(d["returns"]) if "returns" in d else None
        )
        desc = d["desc"] if "desc" in d else None
        return Method(name=name, args=arg_list, returns=return_obj, desc=desc)

    @staticmethod
    def _parse_string(s):
        # Parses a method signature into three tokens, returned as a list:
        # e.g. 'a(b,c)d' -> ['a', 'b,c', 'd']
        stack = []
        for i, char in enumerate(s):
            if char == "(":
                stack.append(i)
            elif char == ")":
                if not stack:
                    break
                left_index = stack[-1]
                stack.pop()
                if not stack:
                    return (s[:left_index], s[left_index + 1 : i], s[i + 1 :])

        raise error.ABIEncodingError(
            "ABI method string has mismatched parentheses: {}".format(s)
        )


class Argument:
    """
    Represents an argument for a ABI method

    Args:
        arg_type (string | Type): ABI type or transaction of the method argument
        name (string, optional): name of this method argument
        desc (string, optional): description of this method argument
    """

    def __init__(self, arg_type, name=None, desc=None) -> None:
        if arg_type in TRANSACTION_ARGS:
            self.type = arg_type
        else:
            # If the type cannot be parsed into an ABI type, it will error
            self.type = type_from_string(arg_type)
        self.name = name
        self.desc = desc

    def __str__(self):
        return str(self.type)

    @staticmethod
    def undictify(d):
        return Argument(
            arg_type=d["type"],
            name=d["name"],
            desc=d["desc"] if "desc" in d else None,
        )


class Returns:
    """
    Represents a return type for a ABI method

    Args:
        arg_type (string): ABI type of this return argument
        desc (string, optional): description of this return argument
    """

    def __init__(self, arg_type, desc=None) -> None:
        if arg_type == "void":
            self.type = arg_type
        else:
            # If the type cannot be parsed into an ABI type, it will error
            self.type = type_from_string(arg_type)
        self.desc = desc

    def __str__(self):
        return str(self.type)

    @staticmethod
    def undictify(d):
        return Returns(
            arg_type=d["type"], desc=d["desc"] if "desc" in d else None
        )