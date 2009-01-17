//
//  Task.m
//  TaskCoach
//
//  Created by Jérôme Laheurte on 14/01/09.
//  Copyright 2009 __MyCompanyName__. All rights reserved.
//

#import "Task.h"

#import "Database.h"
#import "Statement.h"

static Statement *_saveStatement = NULL;

@implementation Task

@synthesize description;
@synthesize startDate;
@synthesize dueDate;
@synthesize completionDate;

- initWithId:(NSInteger)theId name:(NSString *)theName status:(NSInteger)theStatus description:(NSString *)theDescription startDate:(NSDate *)theStartDate dueDate:(NSDate *)theDueDate completionDate:(NSDate *)theCompletionDate;
{
	if (self = [super initWithId:theId name:theName status:theStatus])
	{
		description = [theDescription retain];
		startDate = [theStartDate retain];
		dueDate = [theDueDate retain];
		completionDate = [theCompletionDate retain];
	}
	
	return self;
}

- (void)dealloc
{
	[description release];
	[startDate release];
	[dueDate release];
	[completionDate release];

	[super dealloc];
}

- (Statement *)saveStatement
{
	if (!_saveStatement)
		_saveStatement = [[[Database connection] statementWithSQL:[NSString stringWithFormat:@"UPDATE %@ SET name=?, status=?, description=?, startDate=?, dueDate=?, completionDate=? WHERE id=%d", [self class], objectId]] retain];
	return _saveStatement;
}

- (void)bind
{
	[super bind];
	[[self saveStatement] bindString:description atIndex:3];
	[[self saveStatement] bindInteger:(NSInteger)[startDate timeIntervalSince1970] atIndex:4];
	[[self saveStatement] bindInteger:(NSInteger)[dueDate timeIntervalSince1970] atIndex:5];
	[[self saveStatement] bindInteger:(NSInteger)[completionDate timeIntervalSince1970] atIndex:6];
}

// Overridden setters

- (void)setDescription:(NSString *)descr
{
	[description release];
	description = [descr retain];
	[self setStatus:STATUS_MODIFIED];
}

- (void)setStartDate:(NSDate *)date
{
	[startDate release];
	startDate = [date retain];
	[self setStatus:STATUS_MODIFIED];
}

- (void)setDueDate:(NSDate *)date
{
	[dueDate release];
	dueDate = [date retain];
	[self setStatus:STATUS_MODIFIED];
}

- (void)setCompletionDate:(NSDate *)date
{
	[completionDate release];
	completionDate = [date retain];
	[self setStatus:STATUS_MODIFIED];
}

@end
