function getDateFromCell(cellData){
  try {
    var timeZone = cellData.getTimezoneOffset()/-60;
    timeZone = timeZone > 0 ? "GMT+" + timeZone : "GMT" + timeZone;
    return Utilities.formatDate(new Date(cellData), timeZone, "MMMMM d, yyyy");
  } catch(err) {
    return "" + cellData;
  }
}

function getDataFromLambda() {
  // get data from strava
  var optGet ={
    "method":"get"
  };
  var lambdaURL = "https://***.execute-api.eu-west-1.amazonaws.com/default/***";
  var records = UrlFetchApp.fetch(lambdaURL, optGet).getContentText();
  var recordsArray = JSON.parse(records.replace(new RegExp('\\[.*\\]\s'),'')).content;
  
  // get data from the sheet
  var sheet = SpreadsheetApp.getActiveSheet();
  var data = sheet.getDataRange().getValues();
  var newRecords = [];
  
  for (var iindex = 0; iindex < recordsArray.length; iindex++) {
    // iterate over records from strava
    var toBeAdded = true;
    for (var jindex = 1; jindex < data.length && toBeAdded; jindex++) {
      if (data[jindex][0] == recordsArray[iindex][0] && getDateFromCell(data[jindex][1]) == recordsArray[iindex][1] && Utilities.formatDate(new Date(data[jindex][2]), "GMT+2:03", "h:mm a") == recordsArray[iindex][2]) {
        Logger.log("match found for " + data[jindex] + " " +recordsArray[iindex]);
        toBeAdded = false;
      }
    }
    if(toBeAdded){
      Logger.log("adding " + recordsArray[iindex])
      newRecords.push(recordsArray[iindex]);
    }
  }
  // add new to the sheet
  for(r of newRecords){
    Logger.log(r);
    sheet.appendRow(r);
  }
}
    
// this is a testing function
function testDate() {
   var sheet = SpreadsheetApp.getActiveSheet();
   var data = sheet.getDataRange().getValues();
  
  for (var i = 1; i < data.length; i++) {
    Logger.log(data[i][1]);
    Logger.log(getDateFromCell(data[i][1]) + " " + Utilities.formatDate(new Date(data[i][2]), "GMT+2:03", "h:mm a"));
  }
    
}


