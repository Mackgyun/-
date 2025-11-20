export interface Speaker {
  id: string;
  name: string;
  role: string;
  bio: string;
  topic?: string;
  imageUrl?: string;
}

export interface ScheduleItem {
  time: string;
  title: string;
  speaker?: string;
  description?: string;
}

export interface ScheduleDay {
  date: string;
  location: string;
  items: ScheduleItem[];
}