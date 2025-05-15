<?php
date_default_timezone_set('Asia/Taipei');

$queueDir = "/share/queue/";
$doneDir = "/share/done/";
$runningDir = "/share/running/";

// 請在每個節點依自己身份修改
$nodeName = "computingNode1"; // 例：computingNode1、computingNode2、computingNode3

// 確保 running 目錄存在
if (!is_dir($runningDir)) {
    mkdir($runningDir, 0777, true);
}

$files = glob($queueDir . "*.txt");

// 每次只處理一個任務
if (count($files) === 0) {
    exit(); // 無任務，結束
}

$file = $files[0];
$filename = basename($file);
$parts = explode("_", $filename);

if (count($parts) !== 3) {
    // 不符格式，刪除跳過
    unlink($file);
    exit();
}

$jobId = $parts[0];
$srcLang = $parts[1];
$tgtLang = str_replace(".txt", "", $parts[2]);

$inputText = file_get_contents($file);

if (trim($inputText) === '') {
    file_put_contents($doneDir . "{$jobId}_result.txt", "[Error] Input file is empty.");
    file_put_contents($doneDir . "{$jobId}_start.txt", date("Y-m-d H:i:s"));
    file_put_contents($doneDir . "{$jobId}_end.txt", date("Y-m-d H:i:s"));
    file_put_contents($doneDir . "{$jobId}_node.txt", $nodeName);
    unlink($file);
    exit();
}

// 標記為執行中
file_put_contents($runningDir . "{$jobId}.txt", $nodeName);

// 紀錄開始時間
file_put_contents($doneDir . "{$jobId}_start.txt", date("Y-m-d H:i:s"));

// 執行翻譯
$cmd = "trans -b -no-auto -s $srcLang -t $tgtLang";
$descriptorspec = [
    0 => ["pipe", "r"],  // stdin
    1 => ["pipe", "w"],  // stdout
    2 => ["pipe", "w"]   // stderr
];
$process = proc_open($cmd, $descriptorspec, $pipes);

if (is_resource($process)) {
    fwrite($pipes[0], $inputText);
    fclose($pipes[0]);

    $translated = stream_get_contents($pipes[1]);
    fclose($pipes[1]);

    $stderr = stream_get_contents($pipes[2]);
    fclose($pipes[2]);

    proc_close($process);

    if (trim($translated) === '' && trim($stderr) !== '') {
        $translated = "[Translate Error]\n" . $stderr;
    }

    file_put_contents($doneDir . "{$jobId}_result.txt", $translated);
    file_put_contents($doneDir . "{$jobId}_end.txt", date("Y-m-d H:i:s"));
    file_put_contents($doneDir . "{$jobId}_node.txt", $nodeName);

    // 執行完成，移除 queue 與 running 標記
    unlink($file);
    unlink($runningDir . "{$jobId}.txt");
} else {
    file_put_contents($doneDir . "{$jobId}_result.txt", "[Error] Unable to start translation process.");
    file_put_contents($doneDir . "{$jobId}_end.txt", date("Y-m-d H:i:s"));
    file_put_contents($doneDir . "{$jobId}_node.txt", $nodeName);
    unlink($file);
    unlink($runningDir . "{$jobId}.txt");
}
?>
