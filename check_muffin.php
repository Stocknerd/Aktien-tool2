<?php
require_once('/www/htdocs/w01b3188/schatzsuche40.de/wp-load.php');
$pages = get_posts(array('post_type' => 'page', 'numberposts' => 5));
foreach($pages as $p) {
    if(empty($p->post_title)) continue;
    $meta = get_post_meta($p->ID, 'mfn-page-items', true);
    if($meta) {
        if(is_string($meta)) { 
            $m = @unserialize(base64_decode($meta)); 
            if(!$m) $m = @unserialize($meta); 
        } else {
            $m = $meta;
        }
        if(is_array($m)) {
            echo "Page {$p->ID} ({$p->post_title}):\n";
            // only print the first wrap of the first section
            if(!empty($m[0]['wraps'][0]['items'])) {
                echo json_encode($m[0]['wraps'][0]['items']) . "\n\n";
            }
        }
    }
}
?>
