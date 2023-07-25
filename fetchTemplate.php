<?php

// Trying OOP PHP
// Public can be access from anywhere
// Private can only be access within the class

class jsonUpdate
{

	private $jsonFilePath;
	private $jsonData;

	// This contruct function get automatically activated whenm create new object
	// In this case is file path for JSON files
	public function __construct($jsonfilePath)
	{
		// this keyword is calling object
		$this->jsonFilePath = $jsonFilePath;
		$this->loadData();
	}

	private function loadData()
	{
		$jsonData = file_get_contents($this->jsonFilePath);
		$this->jsonData = json_decode($jsonData, true);
	}

	public function getDropdownOptions()
	{
		$options = '';
		// Try to get scree Name from json file
		foreach ($this->jsonData as $key => $item) {
			$option .= '<option value="' . $key . '">'. $item['screenName'] . '</option>';
		}
		return $options;
	}

	public function updateData($selectedKey, $updateData)
	{
		$this->jsonData[$selectedKey] = $updatedData;
		// pretty print is to add space to json string
		$jsonContent = json_encode($this->jsonData, JSON_PRETTY_PRINT);

		file_put_contents($this->jsonFilePath, $jsonContent);
	}

}

jsonUpdate = new jsonUpdate('/var/www/html/suDevGlassAuomation/cgi-bin/tests/Youtube.json')


// Check if the form is submitted
if ($_SERVER["REQUEST_METHOD"] === "POST" {

	$selectedKey = $_POST['selected_key'];
	$updatedData = array(

	'screenName' => $_POST['screen_name'],
	// Not sure about this but maybe the order of text
	'filePath' => $_POST['file_path']
	'onScreenCords' => explode(',', $_POST['on_screen_cords']),
	'responseCommand' => $_POST['respinse_command'],
	'responseWait' => (int)$_POST['response_wait'],


	$jsonUpdate->updateData($updatedData);

}

$data = $jsonUpdate->getData();


// Generate the dropdown list from screen name
//$screenNames = array_keys[$jsonData];
?>
<!DOCTYPE html>
<html>
<head>
	<title>Dropdown List</title>
</head>
<body>
	<h1>Json Update</h1>

	<form method="post">
		<label for="dataSelect">Select Data:</label>
		<select name="updated_data" id="dataSelect">
		<?php
            // Generate dropdown options from the existing JSON data
		foreach ($data as $key => $value) {
			echo "<option value='$key'>$key</option>";
		}
		?>
		</select>
		<br>
		<label for="updatedValue">Updated Json Data:</label>
		<input type="text" name="updated_value" id="updatedValue" required>
		<br>
		<input type="submit" value="Update Data">
	</form>


</body>
</html>
