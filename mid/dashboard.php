<?php
date_default_timezone_set('Asia/Taipei');

$queueDir = "/share/queue/";
$doneDir = "/share/done/";
$runningDir = "/share/running/";

$nodes = ['computingNode', 'computingNode2', 'computingNode3'];

// 讀取 Queue 任務（排隊中）
$queueFiles = glob($queueDir . "*.txt");
$queueJobs = [];
foreach ($queueFiles as $file) {
    $filename = basename($file);
    $jobId = explode("_", $filename)[0];
    $queueJobs[$jobId] = [
        'jobId' => $jobId,
        'status' => 'Queued',
        'node' => null,
        'start_time' => '',
        'end_time' => '',
    ];
}

// 讀取 Running 任務（執行中）
$runningFiles = glob($runningDir . "*.txt");
$runningJobs = [];
foreach ($runningFiles as $file) {
    $filename = basename($file);
    $jobId = explode("_", $filename)[0];
    $nodeName = file_get_contents($file);
    $runningJobs[$jobId] = [
        'jobId' => $jobId,
        'status' => 'Running',
        'node' => $nodeName,
        'start_time' => file_exists($doneDir . "{$jobId}_start.txt") ? file_get_contents($doneDir . "{$jobId}_start.txt") : '',
        'end_time' => '',
    ];
}

// 讀取 Completed 任務（已完成）
$doneFiles = glob($doneDir . "*_result.txt");
$doneJobs = [];
foreach ($doneFiles as $file) {
    $filename = basename($file);
    $jobId = explode("_", $filename)[0];
    $nodeName = file_exists($doneDir . "{$jobId}_node.txt") ? file_get_contents($doneDir . "{$jobId}_node.txt") : 'Unknown';
    $doneJobs[$jobId] = [
        'jobId' => $jobId,
        'status' => 'Completed',
        'node' => $nodeName,
        'start_time' => file_exists($doneDir . "{$jobId}_start.txt") ? file_get_contents($doneDir . "{$jobId}_start.txt") : '',
        'end_time' => file_exists($doneDir . "{$jobId}_end.txt") ? file_get_contents($doneDir . "{$jobId}_end.txt") : '',
    ];
}

// 合併所有任務（避免重複）
$allJobs = $queueJobs + $runningJobs + $doneJobs;

// 排序：Queued → Running → Completed
usort($allJobs, function($a, $b) {
    $order = ['Queued' => 1, 'Running' => 2, 'Completed' => 3];
    return $order[$a['status']] - $order[$b['status']];
});

// 取得節點 CPU/記憶體使用率
function getNodeStatus($nodeName) {
    $cmd = "docker exec $nodeName top -bn1 -i -c | head -30";
    $output = shell_exec($cmd);
    return $output ? $output : "No data or node offline.";
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>Translation Job Manager Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
<meta http-equiv="refresh" content="10" />
<style>
    pre {
        max-height: 220px;
        overflow-y: scroll;
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 5px;
        font-size: 0.85rem;
    }
</style>
</head>
<body class="bg-light">
<div class="container my-4">
    <h2 class="mb-4">Translation Job Manager Dashboard</h2>
    <h4>Job Status Overview</h4>
    <table class="table table-bordered table-hover table-sm">
        <thead class="table-primary">
            <tr>
                <th>Job ID</th>
                <th>Status</th>
                <th>Processing Node</th>
                <th>Start Time</th>
                <th>End Time</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
            <?php if(empty($allJobs)): ?>
                <tr><td colspan="6" class="text-center">No jobs found.</td></tr>
            <?php else: ?>
                <?php foreach($allJobs as $task): ?>
                    <tr class="<?= $task['status'] == 'Completed' ? 'table-success' : ($task['status'] == 'Running' ? 'table-warning' : '') ?>">
                        <td><?= htmlspecialchars($task['jobId']) ?></td>
                        <td><?= htmlspecialchars($task['status']) ?></td>
                        <td><?= htmlspecialchars($task['node'] ?? '-') ?></td>
                        <td><?= htmlspecialchars($task['start_time']) ?></td>
                        <td><?= htmlspecialchars($task['end_time']) ?></td>
                        <td>
                            <?php if($task['status'] === 'Queued'): ?>
                                <form method="POST" action="delete_task.php" style="margin:0;">
                                    <input type="hidden" name="jobId" value="<?= htmlspecialchars($task['jobId']) ?>">
                                    <button type="submit" class="btn btn-sm btn-danger" onclick="return confirm('Are you sure you want to delete this queued job?');">Delete</button>
                                </form>
                            <?php else: ?>
                                -
                            <?php endif; ?>
                        </td>
                    </tr>
                <?php endforeach; ?>
            <?php endif; ?>
        </tbody>
    </table>
    <h4 class="mt-5">Computing Nodes CPU / Memory Usage</h4>
    <div class="row">
        <?php foreach($nodes as $node): ?>
            <div class="col-md-4 mb-3">
                <h5><?= htmlspecialchars($node) ?></h5>
                <pre><?= htmlspecialchars(getNodeStatus($node)) ?></pre>
            </div>
        <?php endforeach; ?>
    </div>
</div>
</body>
</html>
