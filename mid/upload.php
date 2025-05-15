<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Multi-language File Translator</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-light">

<div class="container mt-5">
    <div class="card shadow-lg">
        <div class="card-header bg-primary text-white text-center">
            <h3><i class="fas fa-language"></i> Multi-language File Translator</h3>
        </div>
        <div class="card-body">
            <form action="exe.php" method="post" enctype="multipart/form-data">
                <div class="mb-3">
                    <label for="file" class="form-label">Select a text file to translate (.txt):</label>
                    <input type="file" class="form-control" name="file" id="file" accept=".txt" required>
                </div>

                <div class="mb-3">
                    <label for="src" class="form-label">Source Language:</label>
                    <select name="src" class="form-select" id="src" required>
                        <option value="en">🇬🇧 English</option>
                        <option value="zh">🇨🇳 Chinese</option>
                        <option value="ja">🇯🇵 Japanese</option>
                        <option value="fr">🇫🇷 French</option>
                    </select>
                </div>

                <div class="mb-3">
                    <label for="tgt" class="form-label">Target Language:</label>
                    <select name="tgt" class="form-select" id="tgt" required>
                        <option value="zh">🇨🇳 Chinese</option>
                        <option value="en">🇬🇧 English</option>
                        <option value="ja">🇯🇵 Japanese</option>
                        <option value="fr">🇫🇷 French</option>
                    </select>
                </div>

                <div class="text-center">
                    <button type="submit" class="btn btn-success px-4"><i class="fas fa-upload"></i> Upload & Translate</button>
                </div>
            </form>
        </div>
        <div class="card-footer text-muted text-center">
            Please upload only UTF-8 encoded .txt files.
        </div>
    </div>
</div>

</body>
</html>
