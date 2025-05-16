<?php
date_default_timezone_set('Asia/Taipei');

// 資料夾設定
$queueDir = "/share/queue/";
$doneDir = "/share/done/";
$runningDir = "/share/running/";

// 請根據當前節點修改名稱
$nodeName = "computingNode1";

// 確保 running 資料夾存在
if (!is_dir($runningDir)) {
    mkdir($runningDir, 0777, true);
}

// ➤ 語言代碼正規化
function normalizeLang($lang) {
    $lang = strtolower($lang);
    if (in_array($lang, ['chinese', 'zh', 'zhtw', 'zh_tw', 'zh-tw'])) {
        return 'zh-tw';
    }
    if (in_array($lang, ['zhcn', 'zh_cn', 'zh-cn', 'chinesesimplified'])) {
        return 'zh-cn';
    }
    return $lang;
}

// ➤ 自動尋找 trans 指令
$transPath = file_exists("/usr/bin/trans") ? "/usr/bin/trans" :
             (file_exists("/usr/local/bin/trans") ? "/usr/local/bin/trans" : null);

if (!$transPath) {
    die("[ERROR] translate-shell (trans) not found in /usr/bin or /usr/local/bin\n");
}

// ➤ 抓取任務檔案
$files = glob($queueDir . "*.txt");
if (count($files) === 0) exit;

$file = $files[0];
$filename = basename($file);
$parts = explode("_", $filename);
if (count($parts) !== 3) {
    unlink($file); // 檔名錯誤
    exit;
}

$jobId = $parts[0];
$srcLang = normalizeLang($parts[1]);
$tgtLang = normalizeLang(str_replace(".txt", "", $parts[2]));

$inputText = file_get_contents($file);
if (trim($inputText) === "") {
    file_put_contents($doneDir . "{$jobId}_result.txt", "[Error] Input file is empty.");
    file_put_contents($doneDir . "{$jobId}_start.txt", date("Y-m-d H:i:s"));
    file_put_contents($doneDir . "{$jobId}_end.txt", date("Y-m-d H:i:s"));
    file_put_contents($doneDir . "{$jobId}_node.txt", $nodeName);
    unlink($file);
    exit;
}

// ➤ 寫入開始與執行中
file_put_contents($doneDir . "{$jobId}_start.txt", date("Y-m-d H:i:s"));
file_put_contents($runningDir . "{$jobId}.txt", $nodeName);

// ➤ 模擬處理時間（便於觀察 Running 狀態）
sleep(5);

// ➤ 構建翻譯指令
$cmd = "$transPath -b -no-auto -s $srcLang -t $tgtLang";

$descriptorspec = [
    0 => ["pipe", "r"], // stdin
    1 => ["pipe", "w"], // stdout
    2 => ["pipe", "w"]  // stderr
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

    if (trim($translated) === "" && trim($stderr) !== "") {
        $translated = "[Translate Error]\n" . $stderr;
    }

    file_put_contents($doneDir . "{$jobId}_result.txt", $translated);
    file_put_contents($doneDir . "{$jobId}_end.txt", date("Y-m-d H:i:s"));
    file_put_contents($doneDir . "{$jobId}_node.txt", $nodeName);

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
