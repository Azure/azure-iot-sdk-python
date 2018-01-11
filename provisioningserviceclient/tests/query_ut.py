# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import unittest
from six import add_move, MovedModule
add_move(MovedModule('mock', 'mock', 'unittest.mock'))
from six.moves import mock

from utils.sastoken import SasTokenFactory
from serviceswagger.operations.device_enrollment_operations import ClientRawResponse
from provisioningserviceclient.models import IndividualEnrollment
from provisioningserviceclient import Query


# Please note that continuation tokens are represented as string representations of ints (or None)
# for the purposes of this unittesting. This is sufficient for our testing purposes, as
# continuation token logic is not within the scope of this testing unit - values are merely
# passed elsewhere. Additionally, doing this allows us to implement simple mocked functionality
# of the layers that do handle them. However, PLEASE BE AWARE that in actual practice,
# these continuation tokens are actually encoded strings.


sas = "dummy-token"
dummy_list = ["dummy", "list"]
version = '2017-11-15'
results = []
for i in range(25):
    results.append(IndividualEnrollment("reg-id-" + str(i), object()))


def get_result(cont_token, pg_size):
    if cont_token is None:
        cont_token = 0
    else:
        cont_token = int(cont_token)
    
    if pg_size is None:
        res = results[cont_token:]
    else:
        pg_size = int(pg_size)
        res = results[cont_token:cont_token+pg_size]
    return res


def get_expected_headers(query, cont_token):
    headers = {}
    headers[query.authorization_header] = sas
    headers[query.continuation_token_header] = cont_token

    if query.page_size is None:
        headers[query.page_size_header] = query.page_size
    else:
        headers[query.page_size_header] = str(query.page_size)
    return headers


def mock_query_op(query_specification, api_version, custom_headers, raw):
    cont_token = custom_headers[Query.continuation_token_header]
    pg_size = custom_headers[Query.page_size_header]

    if cont_token is None:
        cont_token = 0
    else:
        cont_token = int(cont_token)

    page = get_result(cont_token, pg_size)

    if pg_size is None:
        ret_token = None
    else:
        ret_token = cont_token + int(pg_size)
        if ret_token >= len(results) - 1:
            ret_token = None
        else:
            ret_token = str(ret_token)

    cr = ClientRawResponse(page, None)
    cr.headers = {Query.page_size_header: None, 
                  Query.continuation_token_header: ret_token,
                  Query.item_type_header: u'Enrollment'}
    return cr


class TestCaseQueryConstruction(unittest.TestCase):

    def test_construction(self):
        dummy_qs = QuerySpecification("*")
        dummy_factory = SasTokenFactory("dummy", "values", "only")
        dummy_size = 10
        dummy_version = version
        q = Query(dummy_qs, mock_query_op, dummy_factory, dummy_version, dummy_size)
        self.assertEqual(q._query_spec, dummy_qs)
        self.assertEqual(q._query_fn, mock_query_op)
        self.assertEqual(q.page_size, dummy_size)
        self.assertEqual(q._api_version, dummy_version)
        self.assertEqual(q._sastoken_factory, dummy_factory)
        self.assertTrue(q.has_next)
        self.assertIsNone(q.continuation_token)

    def test_construction_no_page(self):
        dummy_qs = QuerySpecification("*")
        dummy_factory = SasTokenFactory("dummy", "values", "only")
        dummy_version = version
        q = Query(dummy_qs, mock_query_op, dummy_factory, dummy_version)
        self.assertEqual(q._query_spec, dummy_qs)
        self.assertEqual(q._query_fn, mock_query_op)
        self.assertEqual(q.page_size, None)
        self.assertEqual(q._api_version, dummy_version)
        self.assertEqual(q._sastoken_factory, dummy_factory)
        self.assertTrue(q.has_next)
        self.assertIsNone(q.continuation_token)


class TestCaseQueryNoPageSize(unittest.TestCase):
    """
    No page size indicates that a full list of results should be expected.
    There will be no paging. All further calls to "next" after the first
    should raise exceptions
    """

    def setUp(self):
        qs = QuerySpecification("*")
        self.querymock = mock.MagicMock(side_effect=mock_query_op)
        sasfactory = SasTokenFactory("dummy", "values", "only")
        self.query = Query(qs, self.querymock, sasfactory, version) 

    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_next_no_page_no_token(self, mock_sas):
        expected_headers = get_expected_headers(self.query, self.query.continuation_token)
        expected_result = get_result(self.query.continuation_token, self.query.page_size)
        res = self.query.next()
        self.assertEqual(res, expected_result)
        self.querymock.assert_called_with(
            self.query._query_spec, self.query._api_version, expected_headers, True)
        with self.assertRaises(StopIteration):
            self.query.next()

    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_next_no_page_w_token(self, mock_sas):
        custom_token = "10"
        expected_headers = get_expected_headers(self.query, custom_token)
        expected_result = get_result(custom_token, self.query.page_size)
        res = self.query.next(custom_token)
        self.assertEqual(res, expected_result)
        self.querymock.assert_called_with(
            self.query._query_spec, self.query._api_version, expected_headers, True)
        with self.assertRaises(StopIteration):
            self.query.next()

    def test_no_page_for_loop(self):
        full_results = []
        count = 0
        for page in self.query:
            count += 1
            full_results += page
        self.assertEqual(full_results, results)
        self.assertEqual(count, 1)


class TestCaseQueryCustomPageSize(unittest.TestCase):

    def setUp(self):
        qs = QuerySpecification("*")
        self.querymock = mock.MagicMock(side_effect=mock_query_op)
        sasfactory = SasTokenFactory("dummy", "values", "only")
        self.query = Query(qs, self.querymock, sasfactory, version, page_size=10) 

    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_next_no_token(self, mock_sas):
        expected_headers = get_expected_headers(self.query, self.query.continuation_token)
        expected_result = get_result(self.query.continuation_token, self.query.page_size)
        res = self.query.next()
        self.assertEqual(res, expected_result)
        self.querymock.assert_called_with(
            self.query._query_spec, self.query._api_version, expected_headers, True)

    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_next_w_token(self, mock_sas):
        custom_token = "10"
        expected_headers = get_expected_headers(self.query, custom_token)
        expected_result = get_result(custom_token, self.query.page_size)
        res = self.query.next(custom_token)
        self.assertEqual(res, expected_result)
        self.querymock.assert_called_with(
            self.query._query_spec, self.query._api_version, expected_headers, True)

    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_next_page_not_full(self, mock_sas):
        custom_token = "20" #although the page size is 10, from this token there are only 5 results
        expected_headers = get_expected_headers(self.query, custom_token)
        expected_result = get_result(custom_token, self.query.page_size)
        res = self.query.next(custom_token)
        self.assertEqual(res, expected_result)
        self.querymock.assert_called_with(
            self.query._query_spec, self.query._api_version, expected_headers, True)

    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_next_custom_page_size(self, mock_sas):
        self.query.page_size = 3
        expected_headers = get_expected_headers(self.query, self.query.continuation_token)
        expected_result = get_result(self.query.continuation_token, self.query.page_size)
        res = self.query.next()
        self.assertEqual(res, expected_result)
        self.querymock.assert_called_with(
            self.query._query_spec, self.query._api_version, expected_headers, True)

    def test_next_has_next_false(self):
        self.query.has_next = False
        with self.assertRaises(StopIteration):
            res = self.query.next()
        self.querymock.assert_not_called()

    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_next_no_more_results_but_has_next_true(self, mock_sas):
        """has_next = True does not guarantee there are actually more results.
        It just means there is more to check for, i.e. has not looked past the end
        of the data to know that it is the end
        """
        custom_token = "25" #there are only 25 results, i.e. start from last index
        expected_headers = get_expected_headers(self.query, custom_token)
        with self.assertRaises(StopIteration):
            res = self.query.next(custom_token)
        self.querymock.assert_called_with(
            self.query._query_spec, self.query._api_version, expected_headers, True)

    def test___iter__(self):
        res = self.query.__iter__()
        self.assertEqual(res, self.query)
        self.assertIsNone(self.query.continuation_token)

    @mock.patch.object(Query, 'next', return_value=dummy_list)
    def test___next__(self, mock_next):
        res = self.query.__next__()
        mock_next.assert_called_with()
        self.assertEqual(res, dummy_list)

    def test_iterate_for_loop(self):
        full_results = []
        for page in self.query:
            full_results += page
        self.assertEqual(full_results, results)

    def test_set_page_size_negative(self):
        with self.assertRaises(ValueError):
            self.query.page_size = -1

    def test_set_page_size_zero(self):
        with self.assertRaises(ValueError):
            self.query.page_size = 0

    def test_set_page_size_positive(self):
        self.query.page_size = 1
        self.assertEqual(self.query.page_size, 1)

    def test_set_page_size_none(self):
        self.query.page_size = None
        self.assertEqual(self.query.page_size, None)

if __name__ == '__main__':
    unittest.main()
