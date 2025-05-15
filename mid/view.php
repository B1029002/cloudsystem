<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Translation Status</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <meta http-equiv="refresh" content="3">
</head>
<body class="bg-light">

<div class="container mt-5">
    <div class="card shadow-lg">
        <div class="card-header bg-warning text-dark">
            <h4 class="mb-0"><i class="fas fa-spinner"></i> Translation Status</h4>
        </div>
        <div class="card-body">
            <?php
            $jobId = $_GET['jobId'];
            $resultFile = "/share/done/{$jobId}_result.txt";
            $startFile = "/share/done/{$jobId}_start.txt";
            $endFile = "/share/done/{$jobId}_end.txt";

            echo "<p><strong>Job ID:</strong> $jobId</p>";

            if (file_exists($startFile)) {
                echo "<p><strong>Started:</strong> " . file_get_contents($startFile) . "</p>";
            }

            if (file_exists($resultFile)) {
                if (!file_exists($endFile)) {
                    file_put_contents($endFile, date("Y-m-d H:i:s"));
                }
                echo "<p><strong>Completed:</strong> " . file_get_contents($endFile) . "</p>";
                echo "<div class='alert alert-success'>Translation Completed:</div>";
                echo "<pre class='p-3 bg-white border rounded'>" . htmlspecialchars(file_get_contents($resultFile)) . "</pre>";
                echo "<a href='download.php?jobId=$jobId' class='btn btn-primary'><i class='fas fa-download'></i> Download Result</a>";
            } else {
                echo "<div class='alert alert-info'>Translation in progress... Refreshing every 3 seconds.</div>";
                echo '<div class="progress mb-2">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 100%">Processing</div>
                      </div>';
            }
            ?>
        </div>
        <div class="card-footer text-center">
            <a href="upload.php" class="btn btn-outline-secondary">Back to Upload Page</a>
        </div>
    </div>
</div>

<!-- FontAwesome -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/js/all.min.js"></script>
</body>
</html>
