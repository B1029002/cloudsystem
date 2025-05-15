<?php
date_default_timezone_set('Asia/Taipei');
if ($_FILES["file"]["error"] > 0) {
    echo "Error: " . $_FILES["file"]["error"];
} else {
    $src = $_POST["src"];
    $tgt = $_POST["tgt"];
    $jobId = microtime(true);
    $dest = "/share/queue/{$jobId}_{$src}_{$tgt}.txt";
    move_uploaded_file($_FILES["file"]["tmp_name"], $dest);

    file_put_contents("/share/done/{$jobId}_start.txt", date("Y-m-d H:i:s"));

    header("Location: view.php?jobId=$jobId");
    exit();
}
?>
