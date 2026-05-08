import xmlrpc.client

WP_USER = "schatzsuche40"
WP_PASS = "VIhSXAT1tAJagL4dR8LJnHWL"

def test_xmlrpc_meta(post_id):
    server = xmlrpc.client.ServerProxy("https://schatzsuche40.de/xmlrpc.php")
    
    custom_fields = [
        {'key': '_yoast_wpseo_metadesc', 'value': 'Dies ist eine XML-RPC Metabeschreibung.'},
        {'key': '_yoast_wpseo_focuskw', 'value': 'XMLRPC Keyword'},
        {'key': '_prosodia_vgw_os_pzm_active', 'value': '1'},
        {'key': '_prosodia_vgw_os_pzm_status', 'value': 'assigned'},
        {'key': 'prosodia_vgw_os_pzm_method', 'value': 'automatic'}
    ]
    
    content = {
        'custom_fields': custom_fields
    }
    
    try:
        res = server.wp.editPost(0, WP_USER, WP_PASS, post_id, content)
        print("XML-RPC Meta Update:", res)
    except Exception as e:
        print("XML-RPC Error:", e)

if __name__ == "__main__":
    test_xmlrpc_meta(1801) # Use the post ID created a minute ago
