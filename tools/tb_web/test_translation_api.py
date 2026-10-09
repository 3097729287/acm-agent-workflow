"""Translation settings HTTP contract; all secrets/state are disposable fixtures."""
import http.client
import json
import unittest
from unittest.mock import patch
from training import ServiceError
from translation import TranslationService
import test_v3_service as v3

class TranslationSettingsHTTPTests(unittest.TestCase):
    request=v3.OverlayHTTPTests.request
    def setUp(self):
        self.detect=patch('translation_config.existing_provider',return_value={});self.detect.start()
        self.local=patch('translation_config.local_key',side_effect=ServiceError(503,'fixture unconfigured'));self.local.start()
        v3.OverlayHTTPTests.setUp(self)
        self.server.translation=TranslationService(object(),self.root)
    def tearDown(self):
        try:v3.OverlayHTTPTests.tearDown(self)
        finally:self.local.stop();self.detect.stop()
    def origin_request(self,origin):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        connection.request('POST','/api/translation/settings',json.dumps({'provider':'deepseek','model':'deepseek-chat'}),
                           {'Content-Type':'application/json','X-TB-Token':self.server.store.token,'Origin':origin})
        response=connection.getresponse();value=json.loads(response.read());status=response.status;connection.close()
        return status,value
    def test_status_then_explicit_provider_configuration_without_network(self):
        status,value=self.request('/api/translation/settings')
        self.assertEqual(status,200);self.assertFalse(value['configured']);self.assertFalse(value['verified'])
        self.assertEqual({provider['id'] for provider in value['providers']},{'deepseek','huoshan'})
        status,value=self.request('/api/translation/settings',{'provider':'huoshan','model':'fixture-model-id'})
        self.assertEqual(status,200);self.assertEqual(value['baseUrl'],'https://ark.cn-beijing.volces.com/api/plan/v3')
        self.assertEqual(value['model'],'fixture-model-id');self.assertFalse(value['configured'])
        self.assertEqual(self.server.training.workspace()['summary']['total'],0)
    def test_secret_dpapi_storage_never_returned_then_can_clear(self):
        secret='tb-fixture-key-12345678901234567890'
        status,value=self.request('/api/translation/settings',{'provider':'deepseek','model':'deepseek-chat','apiKey':secret})
        self.assertEqual(status,200);self.assertTrue(value['configured']);self.assertTrue(value['keyStored'])
        self.assertFalse(value['verified']);self.assertNotIn(secret,json.dumps(value))
        self.assertNotIn('apiKey',value);self.assertNotIn('protectedKey',value)
        self.assertNotIn(secret,(self.root/'translation-settings.json').read_text(encoding='utf-8'))
        self.assertNotIn(secret,json.dumps(self.request('/api/translation/settings')[1]))
        status,value=self.request('/api/translation/settings',{'apiKey':''})
        self.assertEqual(status,200);self.assertFalse(value['keyStored']);self.assertFalse(value['configured'])
    def test_token_and_origin_guards_cannot_change_configuration(self):
        self.assertEqual(self.request('/api/translation/settings',{'provider':'deepseek','model':'deepseek-chat'},token=False)[0],403)
        self.assertEqual(self.origin_request('https://example.org')[0],403)
        self.assertFalse((self.root/'translation-settings.json').exists())
        self.assertEqual(self.origin_request(f'http://127.0.0.1:{self.server.server_port}')[0],200)
    def test_unlisted_provider_endpoint_and_invalid_keys_rejected_without_echo(self):
        for body in ({'provider':'arbitrary'},{'baseUrl':'https://example.org'},{'apiKey':'secret-fixture-invalid!!'},{'model':''}):
            with self.subTest(body=body):
                status,value=self.request('/api/translation/settings',body)
                self.assertEqual(status,422);self.assertNotIn('secret-fixture-invalid!!',json.dumps(value))
        self.assertFalse((self.root/'translation-settings.json').exists())

if __name__=='__main__':unittest.main()
