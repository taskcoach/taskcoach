//
//  TaskDetailsController.m
//  TaskCoach
//
//  Created by Jérôme Laheurte on 19/01/09.
//  Copyright 2009 __MyCompanyName__. All rights reserved.
//

#import "TaskDetailsController.h"
#import "DatePickerViewController.h"

#import "Task.h"

#import "CellFactory.h"
#import "TextFieldCell.h"
#import "DescriptionCell.h"

#import "DateUtils.h"
#import "Database.h"
#import "Statement.h"

//======================================================================

@implementation TaskDetailsController

- initWithTask:(Task *)theTask category:(NSInteger)category
{
	if (self = [super initWithNibName:@"TaskDetails" bundle:[NSBundle mainBundle]])
	{
		task = [theTask retain];
		categoryId = category;

		cells = [[NSMutableArray alloc] initWithCapacity:5];

		SwitchCell *completeCell = [[CellFactory cellFactory] createSwitchCell];
		[completeCell setDelegate:self];
		completeCell.label.text = NSLocalizedString(@"Complete", @"Task details complete label");
		[completeCell.switch_ setOn:(task.completionDate != nil)];
		[cells addObject:completeCell];
		
		TextFieldCell *nameCell = [[CellFactory cellFactory] createTextFieldCell];
		nameCell.textField.delegate = self;
		nameCell.textField.text = task.name;
		[cells addObject:nameCell];
		
		descriptionCell = [[CellFactory cellFactory] createDescriptionCell];
		descriptionCell.textView.delegate = self;
		descriptionCell.textView.text = task.description;
		[cells addObject:descriptionCell];
		
		startDateCell = [[CellFactory cellFactory] createSwitchCell];
		[startDateCell setDelegate:self];
		startDateCell.label.text = NSLocalizedString(@"Start date", @"Task details start date label");
		[startDateCell.switch_ setOn:(task.startDate != nil)];
		[cells addObject:startDateCell];
		
		startDateValueCell = [[UITableViewCell alloc] initWithFrame:CGRectZero];
		startDateValueCell.indentationLevel = 1;
		
		if (task.startDate != nil)
		{
			startDateValueCell.text = task.startDate;
			[cells addObject:startDateValueCell];
		}
		
		dueDateCell = [[CellFactory cellFactory] createSwitchCell];
		[dueDateCell setDelegate:self];
		dueDateCell.label.text = NSLocalizedString(@"Due date", @"Task details due date label");
		[dueDateCell.switch_ setOn:(task.dueDate != nil)];
		[cells addObject:dueDateCell];
		
		dueDateValueCell = [[UITableViewCell alloc] initWithFrame:CGRectZero];
		dueDateValueCell.indentationLevel = 1;
		
		if (task.dueDate != nil)
		{
			dueDateValueCell.text = task.dueDate;
			[cells addObject:dueDateValueCell];
		}
	}

	return self;
}

- (void)dealloc
{
	[task release];
	[cells release];
	[startDateValueCell release];
	[dueDateValueCell release];

	[super dealloc];
}

- (void)saveTask
{
	BOOL isNew = (task.objectId == -1);
	[task save];
	
	if (isNew && (categoryId != -1))
	{
		Statement *req = [[Database connection] statementWithSQL:@"INSERT INTO TaskHasCategory (idTask, idCategory) VALUES (?, ?)"];
		[req bindInteger:task.objectId atIndex:1];
		[req bindInteger:categoryId atIndex:2];
		[req exec];
	}
}

- (void)viewDidLoad
{
	if (task.objectId == -1)
	{
		// New task.
		TextFieldCell *cell = [cells objectAtIndex:1];
		[cell.textField becomeFirstResponder];
		self.navigationItem.title = NSLocalizedString(@"New task", @"New task editing title");
	}
	else
	{
		self.navigationItem.title = task.name;
	}
}

- (void)onSwitchValueChanged:(SwitchCell *)cell
{
	if (cell == startDateCell)
	{
		NSIndexPath *indexPath = [self.tableView indexPathForCell:startDateCell];
		indexPath = [NSIndexPath indexPathForRow:indexPath.row + 1 inSection:indexPath.section];

		if (cell.switch_.on)
		{
			[cells insertObject:startDateValueCell atIndex:indexPath.row];
			[self.tableView insertRowsAtIndexPaths:[NSArray arrayWithObject:indexPath] withRowAnimation:UITableViewRowAnimationRight];

			DatePickerViewController *ctrl = [[DatePickerViewController alloc] initWithDate:task.startDate target:self action:@selector(onPickStartDate:)];
			[self.navigationController presentModalViewController:ctrl animated:YES];
			[ctrl release];
		}
		else
		{
			task.startDate = nil;
			[self saveTask];

			[cells removeObjectAtIndex:indexPath.row];
			[self.tableView deleteRowsAtIndexPaths:[NSArray arrayWithObject:indexPath] withRowAnimation:UITableViewRowAnimationRight];
		}
	}
	else if (cell == dueDateCell)
	{
		NSIndexPath *indexPath = [self.tableView indexPathForCell:dueDateCell];
		indexPath = [NSIndexPath indexPathForRow:indexPath.row + 1 inSection:indexPath.section];
		
		if (cell.switch_.on)
		{
			[cells insertObject:dueDateValueCell atIndex:indexPath.row];
			[self.tableView insertRowsAtIndexPaths:[NSArray arrayWithObject:indexPath] withRowAnimation:UITableViewRowAnimationRight];
			
			DatePickerViewController *ctrl = [[DatePickerViewController alloc] initWithDate:task.dueDate target:self action:@selector(onPickDueDate:)];
			[self.navigationController presentModalViewController:ctrl animated:YES];
			[ctrl release];
		}
		else
		{
			task.dueDate = nil;
			[self saveTask];
			
			[cells removeObjectAtIndex:indexPath.row];
			[self.tableView deleteRowsAtIndexPaths:[NSArray arrayWithObject:indexPath] withRowAnimation:UITableViewRowAnimationRight];
		}
	}
	else
	{
		[task setCompleted:cell.switch_.on];
		[self saveTask];
	}
}

- (void)onPickStartDate:(NSDate *)date
{
	[self.navigationController dismissModalViewControllerAnimated:YES];
	
	if (date)
	{
		task.startDate = [[DateUtils instance] stringFromDate:date];
	}
	else if (!task.startDate)
	{
		[cells removeObject:startDateValueCell];
		NSIndexPath *indexPath = [self.tableView indexPathForCell:startDateValueCell];
		[self.tableView deleteRowsAtIndexPaths:[NSArray arrayWithObject:indexPath] withRowAnimation:UITableViewRowAnimationRight];
		[startDateCell.switch_ setOn:NO animated:YES];
	}
	
	[self saveTask];
	startDateValueCell.text = task.startDate;
}

- (void)onPickDueDate:(NSDate *)date
{
	[self.navigationController dismissModalViewControllerAnimated:YES];
	
	if (date)
	{
		task.dueDate = [[DateUtils instance] stringFromDate:date];
	}
	else if (!task.dueDate)
	{
		[cells removeObject:dueDateValueCell];
		NSIndexPath *indexPath = [self.tableView indexPathForCell:dueDateValueCell];
		[self.tableView deleteRowsAtIndexPaths:[NSArray arrayWithObject:indexPath] withRowAnimation:UITableViewRowAnimationRight];
		[dueDateCell.switch_ setOn:NO animated:YES];
	}
	
	[self saveTask];
	dueDateValueCell.text = task.dueDate;
}

#pragma mark Table view methods

- (NSInteger)numberOfSectionsInTableView:(UITableView *)tableView
{
    return 1;
}

- (NSString *)tableView:(UITableView *)tableView titleForHeaderInSection:(NSInteger)section
{
	return @"";
}

- (NSInteger)tableView:(UITableView *)tableView numberOfRowsInSection:(NSInteger)section
{
	return [cells count];
}

- (UITableViewCell *)tableView:(UITableView *)tableView cellForRowAtIndexPath:(NSIndexPath *)indexPath
{
	return [cells objectAtIndex:indexPath.row];
}

- (void)tableView:(UITableView *)tableView didSelectRowAtIndexPath:(NSIndexPath *)indexPath
{
	UITableViewCell *cell = [cells objectAtIndex:indexPath.row];
	DatePickerViewController *ctrl = nil;

	if (cell == startDateValueCell)
	{
		ctrl = [[DatePickerViewController alloc] initWithDate:task.startDate target:self action:@selector(onPickStartDate:)];
	}
	else if (cell == dueDateValueCell)
	{
		ctrl = [[DatePickerViewController alloc] initWithDate:task.dueDate target:self action:@selector(onPickDueDate:)];
	}

	if (ctrl)
	{
		[self.navigationController presentModalViewController:ctrl animated:YES];
		[ctrl release];
	}
}

- (CGFloat)tableView:(UITableView *)tableView heightForRowAtIndexPath:(NSIndexPath *)indexPath
{
	UITableViewCell *cell = [cells objectAtIndex:indexPath.row];
	
	if (cell == descriptionCell)
		return 160;
	return 44;
}

#pragma mark UITextFieldDelegate protocol

- (BOOL)textFieldShouldReturn:(UITextField *)textField
{
	if ([textField.text length])
	{
		task.name = textField.text;
		[self saveTask];
		[textField resignFirstResponder];
		self.navigationItem.title = task.name;

		return YES;
	}

	return NO;
}

#pragma mark UITextViewDelegate protocol

- (void)textViewDidBeginEditing:(UITextView *)textView
{
	UIBarButtonItem *button = [[UIBarButtonItem alloc] initWithBarButtonSystemItem:UIBarButtonSystemItemSave target:self action:@selector(onSaveDescription:)];
	self.navigationItem.rightBarButtonItem = button;
	[button release];
}

- (void)onSaveDescription:(UIBarButtonItem *)button
{
	self.navigationItem.rightBarButtonItem = nil;
	[descriptionCell.textView resignFirstResponder];
	task.description = descriptionCell.textView.text;
	[self saveTask];
}

@end

