import unittest
from unittest.mock import patch
from datetime import datetime, timezone
import scripts.awin_sync as a

def item(**kwargs):
    return dict(product_name="Tênis Asics Azul",merchant_product_id="123-37",merchant_deep_link="https://www.lauriesporte.com.br/tenis-asics-azul/p?sku=37",aw_deep_link="https://www.awin1.com/pclick.php?p=1&a=2&m=118977",search_price="199,90",currency="BRL",in_stock="1",is_for_sale="1",size="37",**kwargs)

class TestFeed(unittest.TestCase):
    def test_lauri_identity(self):
        x=a.normalize(item(),118977,"Lauri","2026-11-15T14:00:00+00:00")
        self.assertEqual(x["id"],"awin:118977:tenis-asics-azul")
        self.assertEqual(x["group_key"],"shoes")
        self.assertEqual(x["price"],199.9)
        self.assertTrue(x["in_stock"])
    def test_variants(self):
        data=[item(),dict(item(),size="38",search_price="179.90"),dict(item(),size="39",in_stock="0",search_price="9")]
        result=a.combine(a.normalize(x,118977,"Lauri","2026-11-15T14:00:00+00:00") for x in data)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["price"],179.9)
        self.assertEqual(result[0]["sizes"],["37","38"])
        self.assertEqual(result[0]["variant_count"],3)
    def test_no_external_tracking_url(self):
        self.assertIsNone(a.normalize(dict(item(),aw_deep_link="https://example.com"),118977,"Lauri","2026-11-15T14:00:00+00:00"))
    def test_bad_money(self):
        self.assertEqual(a.amount(0),0);self.assertIsNone(a.amount("NaN"));self.assertIsNone(a.amount("-3"));self.assertEqual(a.amount("-3",signed=True),-3)
    def test_csv(self):
        self.assertEqual(a.rows(b'name,price\n"a,b",12\n')[0]["name"],"a,b")
    def test_transaction_attribution(self):
        def tx(id,ref):return dict(id=id,advertiserId=118977,transactionDate="2026-11-15T10:00:00",commissionStatus="approved",type="Sale",clickRefs={"clickRef":ref},saleAmount={"amount":100,"currency":"BRL"},commissionAmount={"amount":10,"currency":"BRL"})
        import json
        with patch.dict(a.os.environ,{"AWIN_PUBLISHER_ID":"123","AWIN_API_TOKEN":"test"}),patch.object(a,"get",return_value=json.dumps([tx(1,"veste-app"),tx(2,"another")]).encode()),patch.object(a,"db") as db,patch.object(a,"log") as log:
            a.sync_transactions()
            data=db.call_args.args[1]["records"]
            self.assertEqual(len(data),1); self.assertEqual(data[0]["id"],"1");self.assertTrue(data[0]["attributed"])
            log.assert_called_once()


    def test_csv_header_and_multiline(self):
        data=('Advertiser ID;Advertiser Name;Membership Status;Datafeed Format;URL\n'
              '118977;"Lauri;\nEsporte";active;Awin;https://productdata.awin.com/example\n').encode()
        rows=a.rows(data)
        self.assertEqual(rows[0]["advertiser_name"],"Lauri;\nEsporte")
        self.assertEqual(a.select_feeds(data,{118977})[118977]["advertiser_id"],"118977")
    def test_csv_long_quoted_field(self):
        data=('name,description,price\n"shoe","'+('long text, with commas\n'*500)+'",100\n').encode()
        self.assertEqual(a.rows(data)[0]["price"],"100")
    def test_csv_reject_partial(self):
        with self.assertRaises(a.SyncIssue):
            a.rows(b'name,price,link\nshoe,100\n')
    def test_google_and_unjoined_excluded(self):
        data=(b'Advertiser ID,Advertiser Name,Membership Status,Datafeed Format,URL\n'
              b'118977,Lauri,active,Google,https://api.awin.com/x\n'
              b'118977,Lauri,pending,Awin,https://productdata.awin.com/x\n')
        self.assertEqual(a.select_feeds(data,{118977}),{})
    def test_legacy_fallback_and_import(self):
        import csv,io
        meta=(b'Merchant ID,Merchant Name,Membership Status,Last Imported,URL\n'
              b'118977,Lauri,active,2026-11-15 14:08:15,https://productdata.awin.com/feed\n')
        output=io.StringIO()
        p=item(); writer=csv.DictWriter(output,fieldnames=p.keys());writer.writeheader();writer.writerow(p)
        with patch.dict(a.os.environ,{"AWIN_PUBLISHER_ID":"123","AWIN_FEED_KEY":"test","AWIN_MERCHANT_IDS":"118977"}),patch.object(a,"request_stage",side_effect=[a.SyncIssue("feed_list_failed"),meta,output.getvalue().encode()]),patch.object(a,"db") as db,patch.object(a,"log") as log:
            a.sync_catalog()
            self.assertEqual(db.call_args.args[0],"rpc/veste_catalog_snapshot_import")
            row=db.call_args.args[1]["records"][0]
            self.assertEqual(row["id"],"awin:118977:tenis-asics-azul")
            self.assertEqual(row["source_updated_at"],"2026-11-15T14:08:15+00:00")
            log.assert_called_once()

if __name__=="__main__":unittest.main()
