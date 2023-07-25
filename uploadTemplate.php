<!DOCTYPE html>
<html>
<head>
    <title>Template Image Submission</title>
</head>
<body>
	<h1>Template Image Submission</h1>
	<form action="<?php echo $_SERVER['PHP_SELF']; ?>" method="POST" enctype="multipart/form-data">
		<label for="screenName">Screen Name:</label>
		<input type="text" name="screenName" id="screenName" required><br><br>

		<label for="filePath">Image File:</label>
		<input type="file" name="imageFile" id="filePath" accept=".png, .jpg, .jpeg" required><br><br>

		<label for="x">X-coordinate:</label>
		<input type="number" name="x" id="x" required><br><br>

		<label for="height">Height:</label>
		<input type="number" name="height" id="height" required><br><br>

		<label for="y">Y-coordinate:</label>
		<input type="number" name="y" id="y" required><br><br>

		<label for="width">Width:</label>
		<input type="number" name="width" id="width" required><br><br>

		<input type="submit" value="Submit">
	</form>
</body>
</html>

<?php
// Retrieve the form data
$screenName = $_POST['screenName'];
$imageFile = $_FILES['imageFile'];
$x = $_POST['x'];
$height = $_POST['height'];
$y = $_POST['y'];
$width = $_POST['width'];

// Verify that the uploaded file is an image
$allowedExtensions = ['png', 'jpg', 'jpeg'];
$fileExtension = strtolower(pathinfo($imageFile['name'], PATHINFO_EXTENSION));
if (!in_array($fileExtension, $allowedExtensions)) {
	die('Error: Only PNG and JPG files are allowed.');
}

// Move the uploaded image to the folder
$destination = '/home/rtglass/glassPanelDev/glassRef' . $imageFile['name'];
move_uploaded_file($imageFile['tmp_name'], $destination);

// Prepare the data to be added to the JSON file
$data = [
	'screenName' => $screenName,
	'filePath' => $destination,
	'onScreenCords' => [$x, $height, $y, $width],
	'responseCommand' => '',
	'responseWait' => 0,
	'textOnScreen' => [],
	'loaded' => 'yes'
];

// Read the existing JSON file
$jsonFile = '/home/rtglass/glassPanelDev/YoutubeSuccessRef.json';
$jsonData = json_decode(file_get_contents($jsonFile), true);

// Assign a new index and add the data to the JSON file
$newIndex = count($jsonData) + 1;
$jsonData[$newIndex] = $data;

// Save the updated JSON data back to the file
file_put_contents($jsonFile, json_encode($jsonData));

echo 'Image submitted successfully';
?>


