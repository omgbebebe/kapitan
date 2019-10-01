#!/usr/bin/env python3
#
# Copyright 2019 The Kapitan Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"refs tests"

import base64
import os
import tempfile
import unittest

from kapitan.errors import RefError, RefFromFuncError, RefHashMismatchError
from kapitan.refs.base import PlainRef, RefController, RefParams, Revealer
from kapitan.refs.base64 import Base64Ref
from kapitan.utils import get_entropy

REFS_HOME = tempfile.mkdtemp()
REF_CONTROLLER = RefController(REFS_HOME)
REVEALER = Revealer(REF_CONTROLLER)


class Base64RefsTest(unittest.TestCase):
    "Test refs"
    def test_plain_ref_compile(self):
        "check plain ref compile() output is not hashed"
        tag = '?{plain:my/ref1_plain}'
        REF_CONTROLLER[tag] = PlainRef(b'ref plain data')
        ref_obj = REF_CONTROLLER[tag]
        compiled = ref_obj.compile()
        self.assertEqual(compiled, 'ref plain data')

    def test_plain_ref_reveal(self):
        "check plain ref reveal() output is original plain data"
        tag = '?{plain:my/ref2_plain}'
        REF_CONTROLLER[tag] = PlainRef(b'ref 2 plain data')
        ref_obj = REF_CONTROLLER[tag]
        revealed = ref_obj.reveal()
        self.assertEqual(revealed, 'ref 2 plain data')

    def test_base64_ref_compile(self):
        "check ref compile() output is valid"
        tag = '?{base64:my/ref1}'
        REF_CONTROLLER[tag] = Base64Ref(b'ref 1 data')
        ref_obj = REF_CONTROLLER[tag]
        compiled = ref_obj.compile()
        self.assertEqual(compiled, '?{base64:my/ref1:3342a45c}')

    def test_base64_ref_recompile(self):
        "check ref recompile() output is valid"
        tag = '?{base64:my/ref1}'
        ref_obj = REF_CONTROLLER[tag]
        compiled = ref_obj.compile()
        self.assertEqual(compiled, '?{base64:my/ref1:3342a45c}')

    def test_base64_ref_update_compile(self):
        "check ref update and compile() output is valid"
        tag = '?{base64:my/ref1}'
        REF_CONTROLLER[tag] = Base64Ref(b'ref 1 more data')
        ref_obj = REF_CONTROLLER[tag]
        compiled = ref_obj.compile()
        self.assertEqual(compiled, '?{base64:my/ref1:ed438a62}')

    def test_base64_ref_reveal(self):
        "check ref reveal() output is valid"
        tag = '?{base64:my/ref2}'
        REF_CONTROLLER[tag] = Base64Ref(b'ref 2 data')
        ref_obj = REF_CONTROLLER[tag]
        revealed = ref_obj.reveal()
        self.assertEqual(revealed, 'ref 2 data')

    def test_base64_ref_non_existent_raises_KeyError(self):
        "check RefController raises KeyError for non existent Base64Ref"
        tag = '?{base64:non/existent}'
        with self.assertRaises(KeyError):
            REF_CONTROLLER[tag]

    def test_base64_ref_tag_type(self):
        "check ref tag type is Base64Ref"
        tag = '?{base64:my/ref3}'
        tag_type = REF_CONTROLLER.tag_type(tag)
        self.assertEqual(tag_type, Base64Ref)

    def test_base64_ref_tag_type_name(self):
        "check ref tag type name is ref"
        tag = '?{base64:my/ref4}'
        tag, token, func_str = REF_CONTROLLER.tag_params(tag)
        type_name = REF_CONTROLLER.token_type_name(token)
        self.assertEqual(tag, '?{base64:my/ref4}')
        self.assertEqual(token, 'base64:my/ref4')
        self.assertEqual(func_str, None)
        self.assertEqual(type_name, 'base64')

    def test_base64_ref_tag_func_name(self):
        "check ref tag func name is correct"
        tag = '?{base64:my/ref5||randomstr}'
        tag, token, func_str = REF_CONTROLLER.tag_params(tag)
        self.assertEqual(tag, '?{base64:my/ref5||randomstr}')
        self.assertEqual(token, 'base64:my/ref5')
        self.assertEqual(func_str, '||randomstr')

    def test_base64_ref_path(self):
        "check ref tag path is correct"
        tag = '?{base64:my/ref6}'
        tag, token, func_str = REF_CONTROLLER.tag_params(tag)
        self.assertEqual(tag, '?{base64:my/ref6}')
        self.assertEqual(token, 'base64:my/ref6')
        self.assertEqual(func_str, None)
        REF_CONTROLLER[tag] = Base64Ref(b'ref 6 data')
        ref_obj = REF_CONTROLLER[tag]
        self.assertEqual(ref_obj.path, 'my/ref6')

    def test_base64_ref_func_raise_RefFromFuncError(self):
        """
        check new ref tag with function raises RefFromFuncError
        and then creates it using RefParams()
        """
        tag = '?{base64:my/ref7||randomstr}'
        with self.assertRaises(RefFromFuncError):
            REF_CONTROLLER[tag]
        try:
            REF_CONTROLLER[tag]
        except RefFromFuncError:
            REF_CONTROLLER[tag] = RefParams()
        REF_CONTROLLER[tag]

    def test_base64_ref_revealer_reveal_raw_data_tag(self):
        "check Revealer reveals raw data"
        tag = '?{base64:my/ref2}'
        data = "data with {}, period.".format(tag)
        revealed_data = REVEALER.reveal_raw(data)
        self.assertEqual(revealed_data, 'data with ref 2 data, period.')

    def test_base64_ref_revealer_reveal_raw_data_tag_compiled_hash(self):
        "check Revealer reveals raw data with compiled tag (with hash)"
        tag = '?{base64:my/ref2}'
        tag_compiled = REF_CONTROLLER[tag].compile()
        data = "data with {}, period.".format(tag_compiled)
        revealed_data = REVEALER.reveal_raw(data)
        self.assertEqual(revealed_data, 'data with ref 2 data, period.')

    def test_base64_ref_revealer_reveal_raw_data_tag_compiled_hash_mismatch(self):
        """
        check Revealer reveals raises RefHashMismatchError
        on mismatch compiled tag hashes
        """
        tag_compiled_hash_mismatch = '?{base64:my/ref2:deadbeef}'
        with self.assertRaises(RefHashMismatchError):
            data = "data with {}, period.".format(tag_compiled_hash_mismatch)
            REVEALER.reveal_raw(data)

    def test_compile_subvars(self):
        """
        test that refs with sub-variables compile properly,
        and refs with different sub-variables stored in the same file has the same hash
        """
        subvar_tag1 = '?{base64:ref/subvars@var1}'
        subvar_tag2 = '?{base64:ref/subvars@var2}'
        REF_CONTROLLER['?{base64:ref/subvars}'] = Base64Ref(b'ref 1 data')
        ref_obj1 = REF_CONTROLLER[subvar_tag1]
        ref_obj2 = REF_CONTROLLER[subvar_tag2]
        self.assertEqual(ref_obj1.compile(), '?{base64:ref/subvars@var1:4357a29b}')
        self.assertEqual(ref_obj2.compile(), '?{base64:ref/subvars@var2:4357a29b}')

    def test_reveal_subvars_raise_RefError(self):
        """
        test that reveal with sub-variable fails should the secret not
        be in valid yaml format
        """
        tag_to_save = '?{base64:ref/subvars_error}'
        yaml_secret = b"this is not yaml"
        REF_CONTROLLER[tag_to_save] = Base64Ref(yaml_secret)
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, 'ref/subvars_error')))

        with self.assertRaises(RefError):
            tag_subvar = '?{base64:ref/subvars_error@var3.var4}'
            data = "message here: {}".format(tag_subvar)
            REVEALER.reveal_raw(data)

    def test_reveal_subvars(self):
        "write yaml secret, and access sub-variables in secrets"
        tag_to_save = '?{base64:ref/subvars}'
        yaml_secret = b"""
        var1:
          var2: hello
        var3:
          var4: world
        """
        REF_CONTROLLER[tag_to_save] = Base64Ref(yaml_secret)
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, 'ref/subvars')))

        tag_subvar = '?{base64:ref/subvars@var1.var2}'
        data = "message here: {}".format(tag_subvar)
        revealed_data = REVEALER.reveal_raw(data)
        self.assertEqual("message here: hello", revealed_data)

        tag_subvar = '?{base64:ref/subvars@var3.var4}'
        data = "message here: {}".format(tag_subvar)
        revealed_data = REVEALER.reveal_raw(data)
        self.assertEqual("message here: world", revealed_data)

        with self.assertRaises(KeyError):
            tag_subvar = '?{base64:ref/subvars@var3.varDoesntExist}'
            data = "message here: {}".format(tag_subvar)
            revealed_data = REVEALER.reveal_raw(data)

    def test_ref_function_randomstr(self):
        "write randomstr to secret, confirm ref file exists, reveal and check"

        tag = '?{base64:ref/randomstr||randomstr}'
        REF_CONTROLLER[tag] = RefParams()
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, 'ref/base64')))

        file_with_tags = tempfile.mktemp()
        with open(file_with_tags, 'w') as fp:
            fp.write('?{base64:ref/randomstr}')
        revealed = REVEALER.reveal_raw_file(file_with_tags)
        self.assertEqual(len(revealed), 43)  # default length of token_urlsafe() string is 43
        self.assertTrue(get_entropy(revealed) > 4)

        # Test with parameter nbytes=16, correlating with string length 16
        tag = '?{base64:ref/randomstr||randomstr:16}'
        REF_CONTROLLER[tag] = RefParams()
        REVEALER._reveal_tag_without_subvar.cache_clear()
        revealed = REVEALER.reveal_raw_file(file_with_tags)
        self.assertEqual(len(revealed), 16)

    def test_ref_function_base64(self):
        "write randomstr to ref and base64, confirm ref file exists, reveal and check"

        tag = '?{base64:ref/base64||randomstr|base64}'
        REF_CONTROLLER[tag] = RefParams()
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, 'ref/base64')))

        file_with_tags = tempfile.mktemp()
        with open(file_with_tags, 'w') as fp:
            fp.write('?{base64:ref/base64}')
        revealed = REVEALER.reveal_raw_file(file_with_tags)
        # If the following succeeds, we guarantee that ref is base64-encoded
        self.assertEqual(base64.b64encode(base64.b64decode(revealed)).decode("UTF-8"), revealed)

    def test_ref_function_sha256(self):
        "write randomstr to ref and sha256, confirm ref file exists, reveal and check"

        tag = '?{base64:ref/sha256||randomstr|sha256}'
        REF_CONTROLLER[tag] = RefParams()
        self.assertTrue(os.path.isfile(os.path.join(REFS_HOME, 'ref/sha256')))

        file_with_tags = tempfile.mktemp()
        with open(file_with_tags, 'w') as fp:
            fp.write('?{base64:ref/sha256}')
        revealed = REVEALER.reveal_raw_file(file_with_tags)
        self.assertEqual(len(revealed), 64)
        try:
            int(revealed, 16)  # sha256 should convert to hex
        except ValueError:
            raise Exception("ref is not sha256 hash")

    # TODO write tests for RefController errors (lookups, etc..)
